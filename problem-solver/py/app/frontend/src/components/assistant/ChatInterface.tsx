import React, { useState, useRef, useEffect } from 'react';
import {
    Card,
    CardContent,
    CardFooter,
    CardHeader,
    CardTitle
} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Textarea} from "@/components/ui/textarea";
import {Avatar} from "@/components/ui/avatar";
import {
    Files,
    FilePlus,
    FileMinus,
    SendHorizonal,
    BrainCircuit,
    User,
    Sparkles
} from "lucide-react";
import {
    cn,
    api,
    type DocumentsInfo,
    type AgentStatus,
    type TaskCategory,
    type FormField,
    type DialogInfo,
    type DialogMessage,
    type ChatResponse,
    type ChatMode
} from '@/library/utils';

interface Message {
    id: string;
    content: string;
    sender: 'user' | 'assistant';
    timestamp: Date;
    meta?: MessageMeta;
}

interface MessageMeta {
    status?: AgentStatus;
    category?: TaskCategory;
    collectedData?: Record<string, string>;
    bestLink?: string | null;
    otherLinks?: string[];
    formFields?: FormField[];
}

const STATUS_LABELS: Record<AgentStatus, string> = {
    question: "Нужна дополнительная информация",
    complete: "Диалог завершен",
    processing: "В обработке",
    error: "Ошибка"
};

const STATUS_STYLES: Record<AgentStatus, string> = {
    question: "bg-amber-100 text-amber-900 border border-amber-200",
    complete: "bg-emerald-100 text-emerald-900 border border-emerald-200",
    processing: "bg-sky-100 text-sky-900 border border-sky-200",
    error: "bg-red-100 text-red-900 border border-red-200"
};

const CATEGORY_LABELS: Record<TaskCategory, string> = {
    informational: "Информационный запрос",
    build_model: "Проектирование модели",
    unclear: "Категория не определена"
};

const ChatInterface: React.FC<{ autoStartMessage?: string | null }> = ({ autoStartMessage = null }) => {
        const [messages, setMessages] = useState<Message[]>([]);

        const [inputValue, setInputValue] = useState('');
        const [isTyping, setIsTyping] = useState(false);
        const [sessionId, setSessionId] = useState<string | null>(null);
        const [isAwaitingDetails, setIsAwaitingDetails] = useState(false);
        const [dialogs, setDialogs] = useState<DialogInfo[]>([]);
        const [isLoadingDialogs, setIsLoadingDialogs] = useState(false);
        const [isLoadingHistory, setIsLoadingHistory] = useState(false);
        const [formFields, setFormFields] = useState<FormField[]>([]);
        const [formValues, setFormValues] = useState<Record<string, string>>({});
        const [pendingAutoMessage, setPendingAutoMessage] = useState<string | null>(autoStartMessage);
        const [showCreateDialog, setShowCreateDialog] = useState(false);
        const [newDialogMode, setNewDialogMode] = useState<ChatMode>("auto");

        const [files, setFiles] = useState<DocumentsInfo[]>([]);

        const [showViewFiles, setShowViewFiles] = useState(false);
        const [showDeleteFiles, setShowDeleteFiles] = useState(false);
        const [showAddFile, setShowAddFile] = useState(false);

        const fileInputRef = useRef<HTMLInputElement | null>(null);
        const viewFilesRef = useRef<HTMLUListElement | null>(null);
        const deleteFilesRef = useRef<HTMLUListElement | null>(null);
        const containerRef = useRef<HTMLDivElement | null>(null);
        const createDialogRef = useRef<HTMLDivElement | null>(null);
        const abortControllerRef = useRef<AbortController | null>(null);
        const activeDialog = sessionId ? dialogs.find(dialog => dialog.session_id === sessionId) : null;

        const applyFormFields = (fields?: FormField[] | null) => {
            if (!fields || fields.length === 0) {
                setFormFields([]);
                setFormValues({});
                return;
            }
            setFormFields(fields);
            const initial: Record<string, string> = {};
            fields.forEach(field => {
                initial[field.name] = field.value ?? "";
            });
            setFormValues(initial);
        };

        const buildMetaFromHistory = (meta?: Record<string, unknown> | null): MessageMeta | undefined => {
            if (!meta) return undefined;
            const result: MessageMeta = {};
            if (typeof meta.status === "string") {
                result.status = meta.status as AgentStatus;
            }
            if (typeof meta.category === "string") {
                result.category = meta.category as TaskCategory;
            }
            if (meta.collected_data && typeof meta.collected_data === "object") {
                result.collectedData = meta.collected_data as Record<string, string>;
            }
            if (typeof meta.best_link === "string") {
                result.bestLink = meta.best_link as string;
            }
            if (Array.isArray(meta.other_links)) {
                result.otherLinks = meta.other_links as string[];
            }
            if (Array.isArray(meta.form_fields)) {
                result.formFields = meta.form_fields as FormField[];
            }
            return Object.keys(result).length ? result : undefined;
        };

        const mapHistoryMessage = (entry: DialogMessage): Message => ({
            id: entry.id,
            content: entry.content,
            sender: entry.role,
            timestamp: new Date(entry.timestamp),
            meta: buildMetaFromHistory(entry.meta ?? undefined)
        });

        const buildMetaFromResponse = (resp: ChatResponse): MessageMeta | undefined => {
            const result: MessageMeta = {};
            if (resp.status) {
                result.status = resp.status;
            }
            if (resp.category) {
                result.category = resp.category;
            }
            if (resp.collected_data) {
                result.collectedData = resp.collected_data;
            }
            if (resp.best_link) {
                result.bestLink = resp.best_link;
            }
            if (resp.other_links && resp.other_links.length > 0) {
                result.otherLinks = resp.other_links;
            }
            if (resp.form_fields && resp.form_fields.length > 0) {
                result.formFields = resp.form_fields;
            }
            return Object.keys(result).length ? result : undefined;
        };

        const summarizeFormValues = (values: Record<string, string>) => {
            const entries = Object.entries(values).filter(([, value]) => value && value.trim().length > 0);
            if (entries.length === 0) return "";
            return [
                "Обновлены параметры:",
                ...entries.map(([key, value]) => `${key}: ${value}`)
            ].join("\n");
        };

        const ensureActiveDialog = async (mode?: ChatMode): Promise<string> => {
            if (sessionId) {
                return sessionId;
            }
            if (dialogs.length > 0) {
                const existing = dialogs[0];
                setSessionId(existing.session_id);
                return existing.session_id;
            }
            const chatMode = mode || newDialogMode;
            const created = await api.createDialog(undefined, chatMode);
            setDialogs(prev => [created, ...prev]);
            setSessionId(created.session_id);
            return created.session_id;
        };
        
        const handleCreateDialog = async (mode?: ChatMode) => {
            try {
                setIsLoadingDialogs(true);
                const chatMode = mode || newDialogMode;
                const created = await api.createDialog(undefined, chatMode);
                setDialogs(prev => [created, ...prev]);
                setSessionId(created.session_id);
                setMessages([]);
                applyFormFields([]);
                setIsAwaitingDetails(false);
                setShowCreateDialog(false);
            } catch (err) {
                console.error("Ошибка создания диалога:", err);
                alert(`Не удалось создать диалог: ${err instanceof Error ? err.message : 'Неизвестная ошибка'}`);
            } finally {
                setIsLoadingDialogs(false);
            }
        };

        const loadHistory = async (dialogId: string) => {
            setIsLoadingHistory(true);
            try {
                const history = await api.getDialogMessages(dialogId);
                const mapped = history.map(mapHistoryMessage);
                setMessages(mapped);
                const pendingAssistant = [...mapped].reverse().find(
                    msg => msg.sender === 'assistant' && msg.meta?.formFields && msg.meta.formFields.length > 0
                );
                applyFormFields(pendingAssistant?.meta?.formFields ?? []);
                setIsAwaitingDetails(Boolean(pendingAssistant?.meta?.formFields && pendingAssistant.meta.formFields.length > 0));
            } catch (err) {
                console.error("Ошибка загрузки диалога:", err);
            } finally {
                setIsLoadingHistory(false);
            }
        };

        const refreshDialogs = async (selectLatest = false) => {
            setIsLoadingDialogs(true);
            try {
                const list = await api.listDialogs();
                setDialogs(list);
                if (selectLatest && list.length > 0) {
                    setSessionId(list[0].session_id);
                }
            } catch (err) {
                console.error("Ошибка загрузки диалогов:", err);
            } finally {
                setIsLoadingDialogs(false);
            }
        };

        const handleSelectDialog = async (dialogId: string) => {
            if (dialogId === sessionId) return;
            
            // Cancel any pending requests when switching dialogs
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
                abortControllerRef.current = null;
            }
            
            setIsTyping(false);
            setIsAwaitingDetails(false);
            setFormFields([]);
            setFormValues({});
            setSessionId(dialogId);
        };

        const handleDeleteDialog = async (dialogId: string, e: React.MouseEvent) => {
            e.stopPropagation();
            if (!confirm(`Удалить диалог "${dialogs.find(d => d.session_id === dialogId)?.title || 'Без названия'}"?`)) {
                return;
            }
            try {
                await api.deleteDialog(dialogId);
                if (sessionId === dialogId) {
                    setSessionId(null);
                    setMessages([]);
                    setIsAwaitingDetails(false);
                    setFormFields([]);
                }
                await refreshDialogs();
            } catch (err) {
                console.error("Ошибка удаления диалога:", err);
                alert("Не удалось удалить диалог");
            }
        };

        const processResponse = (resp: ChatResponse) => {
            setSessionId(resp.session_id);
            const assistantMessage: Message = {
                id: `${Date.now()}-assistant`,
                content: resp.message,
                sender: 'assistant',
                timestamp: new Date(),
                meta: buildMetaFromResponse(resp)
            };
            setMessages(prev => [...prev, assistantMessage]);
            applyFormFields(resp.form_fields);
            const awaiting = resp.status === 'question' || Boolean(resp.form_fields && resp.form_fields.length > 0);
            setIsAwaitingDetails(awaiting);
            void refreshDialogs();
        };

        const handleSendMessage = async (overrideMessage?: string) => {
            const text = (overrideMessage ?? inputValue).trim();
            if (!text) return;
            const dialogId = await ensureActiveDialog();
            const now = Date.now();
            const userMessage: Message = {
                id: `${now}-user`,
                content: text,
                sender: 'user',
                timestamp: new Date()
            };
            setMessages(prev => [...prev, userMessage]);
            if (!overrideMessage) {
                setInputValue('');
            }
            setIsTyping(true);
            try {
                // Get chat_mode from current dialog
                const currentDialog = dialogs.find(d => d.session_id === dialogId);
                const chatMode = currentDialog?.chat_mode as ChatMode | undefined;
                
                const resp = await api.chat({
                    query: text,
                    session_id: dialogId,
                    user_response: isAwaitingDetails ? text : undefined,
                    chat_mode: chatMode
                });
                processResponse(resp);
            } catch (err) {
                console.error("Ошибка чата:", err);
                const description = err instanceof Error ? err.message : 'Неизвестная ошибка';
                const errorMessage: Message = {
                    id: `${Date.now()}-error`,
                    content: `Произошла ошибка при получении ответа. ${description}`,
                    sender: 'assistant',
                    timestamp: new Date(),
                    meta: { status: 'error' }
                };
                setMessages(prev => [...prev, errorMessage]);
                setIsAwaitingDetails(false);
            } finally {
                setIsTyping(false);
            }
        };

        const handleSubmitForm = async () => {
            if (formFields.length === 0) return;
            
            // Check if workflow is already completed by checking last message
            const lastMessage = messages[messages.length - 1];
            if (lastMessage && lastMessage.sender === 'assistant' && lastMessage.meta) {
                // If last message has recommended_model or bestLink, workflow is complete
                if (lastMessage.meta.bestLink || lastMessage.content.includes("Рекомендуемая модель:")) {
                    console.log("Workflow already completed, ignoring form submission");
                    setFormFields([]);
                    setFormValues({});
                    setIsAwaitingDetails(false);
                    return;
                }
            }
            
            const dialogId = await ensureActiveDialog();
            const normalized = Object.fromEntries(
                Object.entries(formValues).map(([key, value]) => [key, value.trim()])
            );
            const summary = summarizeFormValues(normalized);
            if (summary) {
                setMessages(prev => [
                    ...prev,
                    {
                        id: `${Date.now()}-form`,
                        content: summary,
                        sender: 'user',
                        timestamp: new Date()
                    }
                ]);
            }
            
            // Cancel any pending request
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            
            const abortController = new AbortController();
            abortControllerRef.current = abortController;
            
            setIsTyping(true);
            try {
                // Get chat_mode from current dialog
                const currentDialog = dialogs.find(d => d.session_id === dialogId);
                const chatMode = currentDialog?.chat_mode as ChatMode | undefined;
                
                const resp = await api.chat({
                    query: summary || "Отправлены параметры формы",
                    session_id: dialogId,
                    form_data: normalized,
                    chat_mode: chatMode
                });
                
                if (abortController.signal.aborted) {
                    return;
                }
                
                processResponse(resp);
                setFormFields([]);
                setFormValues({});
            } catch (err) {
                if (err instanceof Error && err.name === 'AbortError') {
                    return;
                }
                console.error("Ошибка отправки формы:", err);
            } finally {
                if (!abortController.signal.aborted) {
                    setIsTyping(false);
                }
                abortControllerRef.current = null;
            }
        };



        useEffect(() => {
            const loadFiles = async () => {
                try {
                    const response = await api.getFileList();

                    setFiles(response);
                } catch (err) {
                    console.error("Ошибка загрузки файлов:", err);
                }
            };

            loadFiles();
        }, []);

        useEffect(() => {
            refreshDialogs(true);
        }, []);

        useEffect(() => {
            if (!sessionId) {
                setMessages([]);
                applyFormFields([]);
                setIsAwaitingDetails(false);
                return;
            }
            loadHistory(sessionId);
        }, [sessionId]);

        useEffect(() => {
            if (!pendingAutoMessage) return;
            const send = async () => {
                await handleCreateDialog();
                await handleSendMessage(pendingAutoMessage);
                setPendingAutoMessage(null);
            };
            send();
        }, [pendingAutoMessage]);

        useEffect(() => {
            function handleClickOutside(event: MouseEvent) {
                const target = event.target as Node;
                if (showViewFiles && viewFilesRef.current && !viewFilesRef.current.contains(target) &&
                    !(event.target as HTMLElement).closest('#btn-view-files')) {
                    setShowViewFiles(false);
                }
                if (showDeleteFiles && deleteFilesRef.current && !deleteFilesRef.current.contains(target) &&
                    !(event.target as HTMLElement).closest('#btn-delete-files')) {
                    setShowDeleteFiles(false);
                }
                if (showAddFile && containerRef.current && !containerRef.current.contains(target) &&
                    !(event.target as HTMLElement).closest('#btn-add-file')) {
                    setShowAddFile(false);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                }
                if (showCreateDialog && createDialogRef.current && !createDialogRef.current.contains(target) &&
                    !(event.target as HTMLElement).closest('#btn-create-dialog')) {
                    setShowCreateDialog(false);
                }
            }

            document.addEventListener('mousedown', handleClickOutside);
            return () => document.removeEventListener('mousedown', handleClickOutside);
        }, [showViewFiles, showDeleteFiles, showAddFile, showCreateDialog]);

        const handleKeyPress = (e: React.KeyboardEvent) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        };

        const toggleViewFiles = async () => {
            try {
                if (!showViewFiles) {
                    const currentFiles = await api.getFileList();
                    setFiles(currentFiles);
                }
            setShowViewFiles(!showViewFiles);
            setShowDeleteFiles(false);
            setShowAddFile(false);
            } catch (err) {
                console.error("Ошибка получения списка файлов:", err);
            }
        };

        const toggleDeleteFiles = () => {
            setShowDeleteFiles(!showDeleteFiles);
            setShowViewFiles(false);
            setShowAddFile(false);
        };

        const handleAddFileClick = () => {
            setShowAddFile(true);
            setShowViewFiles(false);
            setShowDeleteFiles(false);
        };

        const handleAddFileCancel = () => {
            setShowAddFile(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        };

        const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
            const fileList = e.target.files;
            if (!fileList?.length) return;

            for (const file of Array.from(fileList)) {
                try {
                    const resp = await api.uploadDoc(file);
                    console.log(`Uploaded id=${resp.file_id}`, resp.message);
                } catch (err) {
                    console.error(err);
                }
            }

            try {
                 const updated = await api.getFileList();
                  setFiles(updated);
            } catch (err) {
                console.error("Не удалось обновить список файлов:", err);
            } finally {
                setShowAddFile(false);
                if (fileInputRef.current) fileInputRef.current.value = '';
            }
        };

        const handleDeleteFile = async (file: DocumentsInfo) => {
            try {
                await api.deleteDoc(file.id);
                const updated = await api.getFileList();
                setFiles(updated);
            } catch (err) {
                console.error("Ошибка удаления файла:", err);
            } finally {
                setShowDeleteFiles(false);
            }
        };

        return (
            <div className="flex h-full gap-4">
                <aside className="w-64 flex flex-col border rounded-lg bg-muted/30 p-3">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-semibold">Диалоги</p>
                        <div className="relative" ref={createDialogRef}>
                            <Button 
                                id="btn-create-dialog"
                                size="icon" 
                                variant="outline" 
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setShowCreateDialog(!showCreateDialog);
                                }} 
                                title="Новый диалог"
                            >
                                <BrainCircuit className="h-4 w-4" />
                            </Button>
                            {showCreateDialog && (
                                <div className="absolute right-0 top-10 z-50 w-48 rounded-md border bg-background shadow-lg p-2 space-y-1">
                                    <p className="text-xs font-semibold px-2 py-1">Выберите тип:</p>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleCreateDialog("auto");
                                        }}
                                        className="w-full text-left px-2 py-1.5 rounded hover:bg-muted text-sm flex items-center gap-2"
                                    >
                                        <Sparkles className="h-4 w-4" />
                                        Автоматически
                                    </button>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleCreateDialog("consultant");
                                        }}
                                        className="w-full text-left px-2 py-1.5 rounded hover:bg-muted text-sm flex items-center gap-2"
                                    >
                                        <User className="h-4 w-4" />
                                        Консультант
                                    </button>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleCreateDialog("designer");
                                        }}
                                        className="w-full text-left px-2 py-1.5 rounded hover:bg-muted text-sm flex items-center gap-2"
                                    >
                                        <BrainCircuit className="h-4 w-4" />
                                        Проектировщик
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="flex-1 overflow-auto space-y-1 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30">
                        {isLoadingDialogs && (
                            <p className="text-xs text-muted-foreground">Загрузка диалогов...</p>
                        )}
                        {!isLoadingDialogs && dialogs.length === 0 && (
                            <p className="text-xs text-muted-foreground">Нет диалогов</p>
                        )}
                        {dialogs.map(dialog => {
                            const getIcon = () => {
                                const mode = dialog.chat_mode || "auto";
                                if (mode === "consultant") {
                                    return <User className="h-4 w-4 text-blue-500" />;
                                } else if (mode === "designer") {
                                    return <BrainCircuit className="h-4 w-4 text-purple-500" />;
                                } else {
                                    return <Sparkles className="h-4 w-4 text-amber-500" />;
                                }
                            };
                            
                            return (
                                <div
                                    key={dialog.session_id}
                                    className={cn(
                                        "w-full rounded-md border px-3 py-2 group relative",
                                        sessionId === dialog.session_id
                                            ? "border-neural-accent bg-neural-accent/10"
                                            : "border-transparent hover:border-muted-foreground/40 hover:bg-muted"
                                    )}
                                >
                                    <button
                                        onClick={() => handleSelectDialog(dialog.session_id)}
                                        className="w-full text-left pr-6 flex items-start gap-2"
                                    >
                                        <div className="mt-0.5 shrink-0">
                                            {getIcon()}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium truncate">{dialog.title ?? "Без названия"}</p>
                                            <p className="text-[0.7rem] text-muted-foreground">
                                                {new Date(dialog.updated_at).toLocaleString()}
                                            </p>
                                        </div>
                                    </button>
                                    <button
                                        onClick={(e) => handleDeleteDialog(dialog.session_id, e)}
                                        className="opacity-0 group-hover:opacity-100 absolute right-2 top-2 p-1 hover:bg-destructive/20 rounded text-destructive text-xs font-bold"
                                        title="Удалить диалог"
                                    >
                                        ×
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                </aside>
                <Card className="flex flex-col flex-1 h-full relative">
                <CardHeader>
                    <CardTitle
                        className="flex flex-wrap items-center gap-2 justify-between"
                    >
                        <div className="flex items-center gap-2 font-semibold text-lg shrink-0">
                            <BrainCircuit className="h-5 w-5 text-neural-accent"/>
                            ИИ-ассистент
                        </div>
                            <div className="flex flex-col text-right text-xs text-muted-foreground max-w-[200px]">
                                <span className="truncate">{activeDialog?.title ?? "Новый диалог"}</span>
                            </div>
                            <div className="flex gap-2 flex-wrap max-w-[65%] sm:max-w-[75%] md:max-w-[85%] justify-end">
                                {/* File buttons retained */}
                            <div className="relative">
                                <Button
                                    id="btn-view-files"
                                    variant="outline"
                                    size="sm"
                                    onClick={toggleViewFiles}
                                    aria-expanded={showViewFiles}
                                    aria-haspopup="listbox"
                                    className="flex items-center gap-1 border-neural-accent text-neural-accent hover:bg-neural-accent/10 focus:ring-1 focus:ring-neural-accent"
                                    title="Посмотреть все файлы"
                                    type="button"
                                >
                                    <Files className="w-4 h-4"/>
                                    Файлы
                                </Button>
                                {showViewFiles && (
                                    <ul
                                        ref={viewFilesRef}
                                        role="listbox"
                                        className="absolute right-0 mt-1 max-h-64 w-48 overflow-auto rounded-md border border-neural-accent bg-neural-primary/90 text-white shadow-lg z-50 backdrop-blur-sm [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-neural-accent/20 hover:[&::-webkit-scrollbar-thumb]:bg-neural-accent/30 [&::-webkit-scrollbar-horizontal]:w-2"
                                        tabIndex={-1}
                                    >
                                        {files.length === 0 && (
                                            <li className="px-3 py-2 text-neutral-400 select-none">
                                                Файлы отсутствуют
                                            </li>
                                        )}
                                        {files.map((file) => (
                                            <li
                                                    key={file.id}
                                                className="px-3 py-2 cursor-default hover:bg-neural-accent/30 rounded select-text break-words text-[0.875rem]"
                                                title={file.filename}
                                            >
                                                {file.filename}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                            <div className="relative">
                                <Button
                                    id="btn-add-file"
                                    variant="outline"
                                    size="sm"
                                    onClick={handleAddFileClick}
                                    title="Добавить файл"
                                    className="flex items-center gap-1 border-neural-accent text-neural-accent hover:bg-neural-accent/10 focus:ring-1 focus:ring-neural-accent"
                                    type="button"
                                >
                                    <FilePlus className="w-4 h-4"/>
                                    Добавить
                                </Button>
                            </div>
                            <div className="relative">
                                <Button
                                    id="btn-delete-files"
                                    variant="outline"
                                    size="sm"
                                    onClick={toggleDeleteFiles}
                                    aria-expanded={showDeleteFiles}
                                    aria-haspopup="listbox"
                                    disabled={files.length === 0}
                                    className={cn(
                                        "flex items-center gap-1 border-neural-accent text-neural-accent hover:bg-neural-accent/10 focus:ring-1 focus:ring-neural-accent",
                                        files.length === 0 ? "opacity-50 cursor-not-allowed" : ""
                                    )}
                                    title="Удалить файл"
                                    type="button"
                                >
                                    <FileMinus className="w-4 h-4"/>
                                    Удалить
                                </Button>
                                {showDeleteFiles && (
                                    <ul
                                        ref={deleteFilesRef}
                                        role="listbox"
                                        className="absolute right-0 mt-1 max-h-64 w-48 overflow-auto rounded-md border border-destructive bg-destructive/90 text-destructive-foreground shadow-lg backdrop-blur-sm z-50 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-neural-accent/20 hover:[&::-webkit-scrollbar-thumb]:bg-neural-accent/30 [&::-webkit-scrollbar-horizontal]:w-2"
                                        tabIndex={-1}
                                    >
                                        {files.length === 0 && (
                                            <li className="px-3 py-2 text-destructive-select-none">
                                                Нет файлов для удаления
                                            </li>
                                        )}
                                        {files.map((file) => (
                                            <li
                                                    key={file.id}
                                                className="px-3 py-2 cursor-pointer hover:bg-destructive-foreground hover:text-destructive rounded select-text break-words text-[0.875rem]"
                                                onClick={() => {
                                                    handleDeleteFile(file);
                                                }}
                                                role="option"
                                                tabIndex={0}
                                                title={file.filename}
                                            >
                                                {file.filename}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        </div>
                    </CardTitle>
                </CardHeader>
                <CardContent
                    className="flex-1 overflow-auto p-4 space-y-4 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-neural-accent/20 hover:[&::-webkit-scrollbar-thumb]:bg-neural-accent/30 [&::-webkit-scrollbar-horizontal]:w-2">
                        {isLoadingHistory && messages.length === 0 && (
                            <div className="flex items-center justify-center text-sm text-muted-foreground h-full">
                                Загрузка диалога...
                            </div>
                        )}
                {messages.map((message) => (
                        <div
                            key={message.id}
                            className={cn(
                                "flex items-start gap-3 max-w-[80%]",
                                message.sender === 'user' ? "ml-auto flex-row-reverse" : ""
                            )}
                        >
                            {message.sender === 'assistant' && (
                                <Avatar className="w-8 h-8 border bg-neural-accent/20">
                                    <BrainCircuit className="h-6 w-6 text-neural-primary"/>
                                </Avatar>
                            )}
                            <div className="max-w-full">
                                <div
                                    className={cn(
                                        "rounded-lg p-3",
                                        message.sender === 'user' ?
                                            "bg-neural-primary text-white" :
                                            "bg-muted"
                                    )}
                                >
                                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    {message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}
                                </p>
                                {message.sender === 'assistant' && message.meta && (
                                    <div className="mt-1 space-y-2">
                                        {message.meta.status && message.meta.status !== 'complete' && (
                                            <div className="flex flex-wrap gap-2 text-[0.7rem]">
                                                <span className={cn("px-2 py-0.5 rounded-full font-medium", STATUS_STYLES[message.meta.status])}>
                                                    {STATUS_LABELS[message.meta.status]}
                                                </span>
                                                {message.meta.category && (
                                                    <span className="px-2 py-0.5 rounded-full border border-border bg-muted text-muted-foreground">
                                                        {CATEGORY_LABELS[message.meta.category]}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                        {message.meta.collectedData && Object.values(message.meta.collectedData).some(Boolean) && (
                                            <div className="rounded border border-dashed border-muted-foreground/40 bg-muted/40 p-2 text-xs space-y-1">
                                                <p className="font-semibold text-muted-foreground">Собранные данные</p>
                                                <ul className="list-disc list-inside space-y-0.5">
                                                    {Object.entries(message.meta.collectedData)
                                                        .filter(([, value]) => Boolean(value))
                                                        .map(([key, value]) => (
                                                            <li key={key}>
                                                                <span className="font-medium">{key}:</span> {value}
                                                            </li>
                                                        ))}
                                                </ul>
                                            </div>
                                        )}
                                        {message.meta.bestLink && (
                                            <div className="text-xs">
                                                <a
                                                    href={message.meta.bestLink}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="text-neural-accent hover:underline break-all"
                                                >
                                                    Лучшая реализация
                                                </a>
                                            </div>
                                        )}
                                        {message.meta.otherLinks && message.meta.otherLinks.length > 0 && (
                                            <details className="text-xs">
                                                <summary className="cursor-pointer text-muted-foreground">Другие ссылки</summary>
                                                <ul className="list-disc list-inside space-y-1 mt-1">
                                                    {message.meta.otherLinks.slice(0, 5).map((link) => (
                                                        <li key={link}>
                                                            <a
                                                                href={link}
                                                                target="_blank"
                                                                rel="noreferrer"
                                                                className="text-primary hover:underline break-all"
                                                            >
                                                                {link}
                                                            </a>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </details>
                                        )}
                                    </div>
                                )}
                            </div>
                            {message.sender === 'user' && (
                                <Avatar className="w-8 h-8 border">
                                    <User className="h-6 w-6"/>
                                </Avatar>
                            )}
                        </div>
                    ))}
                    {isTyping && (
                        <div className="flex items-start gap-3">
                            <Avatar className="w-8 h-8 border bg-neural-accent/20">
                                <BrainCircuit className="h-4 w-4 text-neural-primary"/>
                            </Avatar>
                            <div className="rounded-lg p-3 bg-muted">
                                <div className="flex space-x-1">
                                    <div className="h-2 w-2 rounded-full bg-neural-accent animate-pulse"></div>
                                    <div className="h-2 w-2 rounded-full bg-neural-accent animate-pulse delay-150"></div>
                                    <div className="h-2 w-2 rounded-full bg-neural-accent animate-pulse delay-300"></div>
                                </div>
                            </div>
                        </div>
                    )}
                </CardContent>
                <CardFooter className="border-t p-4 flex flex-col gap-2">
                    {showAddFile && (
                        <div ref={containerRef}
                             className="flex flex-col gap-2 rounded-md border border-neural-accent bg-neural-primary/90 p-3 shadow-lg max-w-sm mx-auto">
                            <div className="flex justify-between items-center">
                                <h4 className="text-sm font-semibold text-white">Добавить файл</h4>
                                <Button size="sm" variant="ghost" onClick={handleAddFileCancel}
                                        className="text-white hover:text-neutral-200 ">Отмена</Button>
                            </div>
                            <input
                                type="file"
                                multiple
                                onChange={handleFileUpload}
                                ref={fileInputRef}
                                className="file-input-bordered file-input file-input-sm w-full rounded-lg bg-neural-accent/50 hover:bg-accent-foreground/50 text-foreground"
                            />
                        </div>
                    )}
                    {formFields.length > 0 && (
                        <div className="w-full rounded-md border border-dashed border-neural-accent/60 bg-muted/40 p-3 space-y-3">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-semibold">Параметры задачи</p>
                                <Button size="sm" onClick={handleSubmitForm} disabled={isTyping}>
                                    Отправить
                                </Button>
                            </div>
                            {formFields.map(field => (
                                <div key={field.name} className="space-y-1">
                                    <p className="text-xs font-semibold">{field.label}</p>
                                    <Textarea
                                        value={formValues[field.name] ?? ""}
                                        onChange={(e) => setFormValues(prev => ({ ...prev, [field.name]: e.target.value }))}
                                        placeholder={field.placeholder ?? undefined}
                                        rows={2}
                                    />
                                    {field.description && (
                                        <p className="text-[0.7rem] text-muted-foreground">{field.description}</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                    {isAwaitingDetails && formFields.length === 0 && (
                        <p className="text-xs text-muted-foreground">
                            Агенту нужны дополнительные сведения. Ответьте на вопрос выше, чтобы продолжить.
                        </p>
                    )}
                    <div className="flex gap-2 w-full">
                        <Textarea
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyPress}
                            placeholder={isAwaitingDetails ? "Введите ответ для уточнения данных..." : "Напишите сообщение..."}
                            className="flex-1 min-h-[40px] resize-none"
                            rows={1}
                            disabled={showAddFile}
                        />
                        <Button
                            onClick={() => handleSendMessage()}
                            disabled={!inputValue.trim() || showAddFile || isTyping}
                            className="shrink-0"
                        >
                            <SendHorizonal className="h-5 w-5"/>
                            <span className="sr-only">Отправить</span>
                        </Button>
                    </div>
                </CardFooter>
            </Card>
        </div>
        );
    };

export default ChatInterface;
