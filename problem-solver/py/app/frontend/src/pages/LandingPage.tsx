import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Brain, Zap, Shield, ArrowRight, LogIn } from 'lucide-react';
import LoginDialog from '@/components/auth/LoginDialog';

const LandingPage = () => {
  const [isLoginDialogOpen, setIsLoginDialogOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted">
      {/* Header with Login Button */}
      <header className="container mx-auto px-4 py-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Brain className="h-8 w-8 text-neural-primary" />
            <h1 className="text-2xl font-bold">OSTIS-ANN</h1>
          </div>
          <Button
            onClick={() => setIsLoginDialogOpen(true)}
            className="flex items-center gap-2"
          >
            <LogIn className="h-4 w-4" />
            Войти
          </Button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center space-y-8 mb-16">
          <h2 className="text-5xl font-bold tracking-tight">
            Платформа для работы с искусственными нейронными сетями
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Создавайте, обучайте и сравнивайте модели нейронных сетей с помощью современного интерфейса и мощных инструментов
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-16">
          <Card>
            <CardHeader>
              <Brain className="h-10 w-10 text-neural-primary mb-2" />
              <CardTitle>Создание моделей</CardTitle>
              <CardDescription>
                Проектируйте архитектуры нейронных сетей с интуитивным интерфейсом
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <Zap className="h-10 w-10 text-neural-accent mb-2" />
              <CardTitle>Обучение моделей</CardTitle>
              <CardDescription>
                Обучайте модели на ваших данных с настройкой параметров обучения
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <Shield className="h-10 w-10 text-neural-secondary mb-2" />
              <CardTitle>Безопасность</CardTitle>
              <CardDescription>
                Защищённая аутентификация и управление доступом к вашим проектам
              </CardDescription>
            </CardHeader>
          </Card>
        </div>

        {/* CTA Section */}
        <div className="text-center space-y-4">
          <Button
            size="lg"
            onClick={() => setIsLoginDialogOpen(true)}
            className="flex items-center gap-2 mx-auto"
          >
            Начать работу
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </main>

      {/* Login Dialog */}
      <LoginDialog
        open={isLoginDialogOpen}
        onOpenChange={setIsLoginDialogOpen}
      />
    </div>
  );
};

export default LandingPage;