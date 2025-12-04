
import React, { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle, CardFooter, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import StatCard from '@/components/dashboard/StatCard';
import ModelCard from '@/components/neural/ModelCard';
import { Textarea } from "@/components/ui/textarea";
import { BarChart, Brain, Construction, Clock, ArrowRight, SendHorizonal } from 'lucide-react';
import { sampleModels } from '@/library/sampleData';
import { useNavigate } from "react-router-dom";

const Index = () => {
  const [quickPrompt, setQuickPrompt] = useState("");
  const navigate = useNavigate();

  const handleQuickSubmit = () => {
    const trimmed = quickPrompt.trim();
    if (!trimmed) return;
    navigate(`/create?prefill=${encodeURIComponent(trimmed)}`);
  };
  // Get only the first 3 models for the recent models section
  const recentModels = sampleModels.slice(0, 3);

  return (
    <MainLayout>
      <div className="container mx-auto p-4 md:p-6 space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1">Панель управления</h1>
          <p className="text-muted-foreground">Обзор ваших проектов и активности</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            title="Всего моделей"
            value="18"
            icon={<Brain className="h-5 w-5 text-neural-primary" />}
            trend={{ value: 12, isPositive: true }}
          />
          <StatCard 
            title="Обучено за неделю"
            value="5"
            icon={<Construction className="h-5 w-5 text-neural-accent" />}
            trend={{ value: 20, isPositive: true }}
          />
          <StatCard 
            title="Среднее время обучения"
            value="14.2 мин"
            icon={<Clock className="h-5 w-5 text-neural-secondary" />}
            trend={{ value: 5, isPositive: false }}
          />
          <StatCard 
            title="Сравнений моделей"
            value="7"
            icon={<BarChart className="h-5 w-5 text-neural-info" />}
            trend={{ value: 15, isPositive: true }}
          />
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Последние модели</h2>
                <Button variant="outline" size="sm" className="flex items-center gap-1">
                  <span>Посмотреть все</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {recentModels.map(model => (
                  <ModelCard key={model.id} model={model} />
                ))}
              </div>
            </div>
            
            <div>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Активные проекты</h2>
                <Button variant="outline" size="sm" className="flex items-center gap-1">
                  <span>Все проекты</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
              <div className="grid grid-cols-1 gap-4">
                <Card>
                  <CardContent className="p-0">
                    <div className="divide-y">
                      {['Классификация документов', 'Распознавание лиц', 'Прогноз продаж'].map((project, i) => (
                        <div key={i} className="flex items-center justify-between py-4 px-6">
                          <div>
                            <h3 className="font-medium">{project}</h3>
                            <p className="text-sm text-muted-foreground">Последнее обновление: {new Date().toLocaleDateString()}</p>
                          </div>
                          <Button size="sm">Открыть</Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
          
          <div>
            <Card className="h-[600px] flex flex-col">
              <CardHeader>
                <CardTitle>Быстрый запрос</CardTitle>
                <CardDescription>Введите описание задачи, и мы перенаправим вас в конструктор ИНС</CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <Textarea
                  value={quickPrompt}
                  onChange={(e) => setQuickPrompt(e.target.value)}
                  placeholder="Например: Нужно распознать кошек и собак по фотографиям..."
                  className="h-full resize-none"
                />
              </CardContent>
              <CardFooter className="justify-end">
                <Button
                  onClick={handleQuickSubmit}
                  disabled={!quickPrompt.trim()}
                  className="flex items-center gap-2"
                >
                  Перейти в конструктор
                  <SendHorizonal className="h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default Index;
