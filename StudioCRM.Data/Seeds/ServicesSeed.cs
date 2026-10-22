using StudioCRM.Core.Enums;
using StudioCRM.Core.Models;

namespace StudioCRM.Data.Seeds;

public static class ServicesSeed
{
    public static List<ServiceItem> GetServices()
    {
        return new List<ServiceItem>
        {
            // === ВЕБ-РАЗРАБОТКА (1-10) ===
            new() { Category = "Веб-разработка", Title = "Разработка лендинга (Landing Page)", BillingType = BillingType.Fix, DefaultPrice = 45000, Unit = "проект", Description = "Одностраничный промо-сайт с конверсионными блоками и адаптивной версткой" },
            new() { Category = "Веб-разработка", Title = "Корпоративный многостраничный сайт", BillingType = BillingType.Fix, DefaultPrice = 120000, Unit = "проект", Description = "Сайт компании: разделы о нас, услуги, блог, контакты, панель управления" },
            new() { Category = "Веб-разработка", Title = "Интернет-магазин под ключ (E-commerce)", BillingType = BillingType.Fix, DefaultPrice = 250000, Unit = "проект", Description = "Каталог, корзина, онлайн-оплата, складской учет, личный кабинет покупателя" },
            new() { Category = "Веб-разработка", Title = "Разработка SPA-приложения (React/Vue)", BillingType = BillingType.Fix, DefaultPrice = 180000, Unit = "проект", Description = "Интерактивное веб-приложение с динамическим роутингом и стейт-менеджментом" },
            new() { Category = "Веб-разработка", Title = "Разработка Backend API (.NET / C#)", BillingType = BillingType.Hourly, DefaultPrice = 3500, Unit = "час", Description = "Проектирование архитектуры, REST/GraphQL API, бизнес-логика, интеграция с БД" },
            new() { Category = "Веб-разработка", Title = "Интеграция платежного шлюза (ЮKassa/Тинькофф)", BillingType = BillingType.Fix, DefaultPrice = 25000, Unit = "интеграция", Description = "Подключение интернет-эквайринга, чеков 54-ФЗ и webhook-уведомлений" },
            new() { Category = "Веб-разработка", Title = "Интеграция с 1С / МойСклад", BillingType = BillingType.Fix, DefaultPrice = 60000, Unit = "интеграция", Description = "Двусторонняя синхронизация остатков, цен, заказов и контрагентов" },
            new() { Category = "Веб-разработка", Title = "Аудит и рефакторинг легаси-кода", BillingType = BillingType.Hourly, DefaultPrice = 4000, Unit = "час", Description = "Анализ узких мест, устранение техдолга, улучшение архитектуры" },
            new() { Category = "Веб-разработка", Title = "Разработка Telegram Mini App", BillingType = BillingType.Fix, DefaultPrice = 90000, Unit = "проект", Description = "Веб-приложение внутри мессенджера Telegram с авторизацией и оплатами" },
            new() { Category = "Веб-разработка", Title = "Разработка личного кабинета (B2B/B2C)", BillingType = BillingType.Fix, DefaultPrice = 200000, Unit = "проект", Description = "Пользовательский дашборд, документы, заказы, управление доступами" },

            // === МОБИЛЬНАЯ РАЗРАБОТКА (11-18) ===
            new() { Category = "Мобильная разработка", Title = "Разработка кроссплатформенного приложения (Flutter)", BillingType = BillingType.Fix, DefaultPrice = 350000, Unit = "проект", Description = "Единая кодовая база для iOS и Android с нативной производительностью" },
            new() { Category = "Мобильная разработка", Title = "Нативная разработка iOS (Swift)", BillingType = BillingType.Hourly, DefaultPrice = 4000, Unit = "час", Description = "Приложение для iPhone и iPad с соблюдением Human Interface Guidelines" },
            new() { Category = "Мобильная разработка", Title = "Нативная разработка Android (Kotlin)", BillingType = BillingType.Hourly, DefaultPrice = 3800, Unit = "час", Description = "Приложение под Android с Material Design 3 и архитектурой Jetpack" },
            new() { Category = "Мобильная разработка", Title = "Публикация в App Store и Google Play", BillingType = BillingType.Fix, DefaultPrice = 20000, Unit = "пакет", Description = "Подготовка скриншотов, метаданных, прохождение ревью и модерации" },
            new() { Category = "Мобильная разработка", Title = "Интеграция Push-уведомлений (FCM/OneSignal)", BillingType = BillingType.Fix, DefaultPrice = 18000, Unit = "услуга", Description = "Сегментированные и триггерные push-уведомления для удержания пользователей" },
            new() { Category = "Мобильная разработка", Title = "In-App Purchases и подписки", BillingType = BillingType.Fix, DefaultPrice = 35000, Unit = "услуга", Description = "Подключение покупок внутри приложения, автопродление подписок и чеки" },
            new() { Category = "Мобильная разработка", Title = "Оптимизация производительности приложения", BillingType = BillingType.Hourly, DefaultPrice = 3500, Unit = "час", Description = "Профилирование памяти, плавность анимаций 60/120fps, ускорение cold start" },
            new() { Category = "Мобильная разработка", Title = "Разработка мобильного UI Kit", BillingType = BillingType.Fix, DefaultPrice = 50000, Unit = "комплект", Description = "Библиотека переиспользуемых компонентов интерфейса для мобильных экранов" },

            // === UI/UX ДИЗАЙН (19-27) ===
            new() { Category = "UI/UX Дизайн", Title = "UX-исследование и CJM (Customer Journey Map)", BillingType = BillingType.Fix, DefaultPrice = 50000, Unit = "исследование", Description = "Глубинные интервью, карта пути пользователя, выявление болей и барьеров" },
            new() { Category = "UI/UX Дизайн", Title = "Интерактивный кликабельный прототип в Figma", BillingType = BillingType.Fix, DefaultPrice = 40000, Unit = "прототип", Description = "Wireframes основных пользовательских сценариев для быстрого тестирования" },
            new() { Category = "UI/UX Дизайн", Title = "Дизайн концепт главной страницы / экрана", BillingType = BillingType.Fix, DefaultPrice = 25000, Unit = "концепт", Description = "2-3 уникальных стилистических направления на выбор клиента" },
            new() { Category = "UI/UX Дизайн", Title = "Комплексный UI-дизайн веб-сервиса", BillingType = BillingType.Fix, DefaultPrice = 130000, Unit = "проект", Description = "Проработка всех страниц, состояний кнопок, форм, модалок и адаптивных версий" },
            new() { Category = "UI/UX Дизайн", Title = "Создание дизайн-системы и UI Kit", BillingType = BillingType.Fix, DefaultPrice = 75000, Unit = "система", Description = "Цветовая палитра, типографика, сетки, токены и автолейаут-компоненты" },
            new() { Category = "UI/UX Дизайн", Title = "Редизайн существующего продукта", BillingType = BillingType.Fix, DefaultPrice = 90000, Unit = "проект", Description = "Осовременивание визуального языка, исправление UX-ошибок и повышение конверсии" },
            new() { Category = "UI/UX Дизайн", Title = "3D-иллюстрации и графика для сайта", BillingType = BillingType.Fix, DefaultPrice = 35000, Unit = "комплект", Description = "Сет уникальных рендеров в единой стилистике для брендинга" },
            new() { Category = "UI/UX Дизайн", Title = "Дизайн иконок и пиктограмм", BillingType = BillingType.Fix, DefaultPrice = 15000, Unit = "пак", Description = "Векторный пак фирменных иконок 24x24 / 32x32 под проект" },
            new() { Category = "UI/UX Дизайн", Title = "UI/UX Экспресс-аудит проекта", BillingType = BillingType.Fix, DefaultPrice = 20000, Unit = "отчет", Description = "Отчет с разбором ошибок юзабилити, эвристиками Нильсена и точками роста" },

            // === QA & ТЕСТИРОВАНИЕ (28-34) ===
            new() { Category = "QA & Тестирование", Title = "Ручное функциональное тестирование (Manual QA)", BillingType = BillingType.Hourly, DefaultPrice = 2200, Unit = "час", Description = "Тест-кейсы, чек-листы, регрессионное тестирование и баг-репорты" },
            new() { Category = "QA & Тестирование", Title = "Разработка E2E автотестов (Playwright/Cypress)", BillingType = BillingType.Hourly, DefaultPrice = 3200, Unit = "час", Description = "Автоматизация ключевых пользовательских сценариев для непрерывного CI" },
            new() { Category = "QA & Тестирование", Title = "Нагрузочное тестирование (k6 / JMeter)", BillingType = BillingType.Fix, DefaultPrice = 65000, Unit = "тест-пакет", Description = "Имитация пиковых нагрузок, поиск узких мест БД и пропускной способности" },
            new() { Category = "QA & Тестирование", Title = "Аудит информационной безопасности (PenTest)", BillingType = BillingType.Fix, DefaultPrice = 110000, Unit = "аудит", Description = "Поиск OWASP Top-10 уязвимостей, проверка авторизации и защиты данных" },
            new() { Category = "QA & Тестирование", Title = "Кроссбраузерное и мобильное тестирование", BillingType = BillingType.Fix, DefaultPrice = 25000, Unit = "прогон", Description = "Проверка на реальных устройствах: iOS Safari, Chrome Android, Edge, Firefox" },
            new() { Category = "QA & Тестирование", Title = "Тестирование API и интеграций (Postman/Newman)", BillingType = BillingType.Fix, DefaultPrice = 30000, Unit = "коллекция", Description = "Коллекции автотестов параметров, статус-кодов, валидации схем и заголовков" },
            new() { Category = "QA & Тестирование", Title = "Составление тест-плана и матрицы покрытия", BillingType = BillingType.Fix, DefaultPrice = 20000, Unit = "документ", Description = "Формализованная документация процесса обеспечения качества" },

            // === DEVOPS & ИНФРАСТРУКТУРА (35-42) ===
            new() { Category = "DevOps & Инфраструктура", Title = "Настройка CI/CD пайплайна (GitHub Actions/GitLab)", BillingType = BillingType.Fix, DefaultPrice = 40000, Unit = "пайплайн", Description = "Автоматическая сборка, запуск тестов, линтеров и деплой на staging/prod" },
            new() { Category = "DevOps & Инфраструктура", Title = "Контейнеризация сервисов (Docker & Compose)", BillingType = BillingType.Fix, DefaultPrice = 25000, Unit = "стек", Description = "Оптимизированные multi-stage Dockerfile, docker-compose для локальной разработки" },
            new() { Category = "DevOps & Инфраструктура", Title = "Развертывание кластера Kubernetes (k8s)", BillingType = BillingType.Fix, DefaultPrice = 140000, Unit = "кластер", Description = "Helm-чарты, ingress, cert-manager, автоскейлинг HPA и отказоустойчивость" },
            new() { Category = "DevOps & Инфраструктура", Title = "Базовая настройка VPS/VDS Linux сервера", BillingType = BillingType.Fix, DefaultPrice = 15000, Unit = "сервер", Description = "Hardening SSH, UFW firewall, fail2ban, Nginx reverse-proxy, SSL Let's Encrypt" },
            new() { Category = "DevOps & Инфраструктура", Title = "Система мониторинга и алертинга (Prometheus+Grafana)", BillingType = BillingType.Fix, DefaultPrice = 50000, Unit = "система", Description = "Сбор метрик CPU/RAM/диска, дашборды сервисов и алерты в Telegram" },
            new() { Category = "DevOps & Инфраструктура", Title = "Централизованное логирование (Loki / ELK)", BillingType = BillingType.Fix, DefaultPrice = 45000, Unit = "система", Description = "Агрегация логов со всех сервисов и контейнеров с быстрым поиском" },
            new() { Category = "DevOps & Инфраструктура", Title = "Настройка автоматических бэкапов и Disaster Recovery", BillingType = BillingType.Fix, DefaultPrice = 25000, Unit = "конфиг", Description = "Ежедневные зашифрованные дампы БД в S3 хранилище с ротацией" },
            new() { Category = "DevOps & Инфраструктура", Title = "Миграция инфраструктуры в облако (Яндекс.Облако/VK)", BillingType = BillingType.Fix, DefaultPrice = 85000, Unit = "миграция", Description = "Бесшовный перенос данных и сервисов с минимальным downtime" },

            // === МАРКЕТИНГ & SEO (43-48) ===
            new() { Category = "Маркетинг & SEO", Title = "Комплексный технический и поисковый SEO-аудит", BillingType = BillingType.Fix, DefaultPrice = 35000, Unit = "аудит", Description = "Анализ индексации, дублей, скорости Core Web Vitals, ссылочной массы" },
            new() { Category = "Маркетинг & SEO", Title = "Сбор широкого семантического ядра и кластеризация", BillingType = BillingType.Fix, DefaultPrice = 30000, Unit = "ядро", Description = "Ключевые фразы, группировка по посадочным страницам, частотность" },
            new() { Category = "Маркетинг & SEO", Title = "Настройка рекламы Яндекс.Директ (Поиск + РСЯ)", BillingType = BillingType.Fix, DefaultPrice = 40000, Unit = "кампания", Description = "Сегментация аудиторий, минус-слова, A/B тесты креативов и UTM-разметка" },
            new() { Category = "Маркетинг & SEO", Title = "Ведение контекстной рекламы", BillingType = BillingType.AdBudget, DefaultPrice = 15, Unit = "% бюджета", Description = "Ежемесячная оптимизация ставок, чистка площадок и снижение стоимости лида" },
            new() { Category = "Маркетинг & SEO", Title = "Таргетированная реклама (VK Реклама / Telegram Ads)", BillingType = BillingType.Fix, DefaultPrice = 35000, Unit = "кампания", Description = "Парсинг целевых сообществ, настройка пикселей ретаргетинга и запуск" },
            new() { Category = "Маркетинг & SEO", Title = "Копирайтинг экспертных SEO-статей для блога", BillingType = BillingType.Fix, DefaultPrice = 5000, Unit = "статья", Description = "Тексты от 5000 знаков с LSI-фразами, структурой H1-H3 и уникальностью 95%+" },

            // === АНАЛИТИКА & ДАННЫЕ (49-54) ===
            new() { Category = "Аналитика & Данные", Title = "Настройка Яндекс.Метрики и Google Analytics 4", BillingType = BillingType.Fix, DefaultPrice = 20000, Unit = "настройка", Description = "Электронная коммерция, составные цели, отслеживание форм и событий" },
            new() { Category = "Аналитика & Данные", Title = "Внедрение сквозной аналитики (Roistat / Calltouch)", BillingType = BillingType.Fix, DefaultPrice = 60000, Unit = "проект", Description = "Интеграция CRM + Реклама + Телефония для расчета точного CPL/LTV/ROI" },
            new() { Category = "Аналитика & Данные", Title = "Разработка BI-дашборда для руководства (PowerBI/Superset)", BillingType = BillingType.Fix, DefaultPrice = 70000, Unit = "дашборд", Description = "Ключевые бизнес-метрики студии, выручка, конверсии воронок в реальном времени" },
            new() { Category = "Аналитика & Данные", Title = "Разработка парсера данных / скрапера (Python)", BillingType = BillingType.Fix, DefaultPrice = 35000, Unit = "парсер", Description = "Сбор данных с сайтов-конкурентов, маркетплейсов, обход капчи и прокси" },
            new() { Category = "Аналитика & Данные", Title = "А/B тестирование посадочных страниц", BillingType = BillingType.Fix, DefaultPrice = 30000, Unit = "тест", Description = "Статистическая проверка гипотез, замер конверсий альтернативных заголовков и CTA" },
            new() { Category = "Аналитика & Данные", Title = "Проектирование архитектуры базы данных (PostgreSQL)", BillingType = BillingType.Fix, DefaultPrice = 45000, Unit = "схема", Description = "Нормализация, индексы, партиционирование и проектирование связей" },

            // === ПОДДЕРЖКА & SLA (55-58) ===
            new() { Category = "Поддержка & SLA", Title = "Техническая поддержка проекта (Тариф Базовый)", BillingType = BillingType.Monthly, DefaultPrice = 30000, Unit = "месяц", Description = "До 15 часов работ в месяц, мониторинг доступности 99.5%, время реакции до 4ч" },
            new() { Category = "Поддержка & SLA", Title = "Техническая поддержка (Тариф Pro / SLA 24/7)", BillingType = BillingType.Monthly, DefaultPrice = 80000, Unit = "месяц", Description = "До 45 часов в месяц, аварийная реакция 15 минут, выделенный дежурный инженер" },
            new() { Category = "Поддержка & SLA", Title = "Обновление CMS / фреймворков и библиотек", BillingType = BillingType.Fix, DefaultPrice = 25000, Unit = "релиз", Description = "Переход на актуальные версии с сохранением работоспособности всех модулей" },
            new() { Category = "Поддержка & SLA", Title = "Технический аудит и ускорение загрузки сайта", BillingType = BillingType.Fix, DefaultPrice = 35000, Unit = "проект", Description = "Сжатие медиа, минификация JS/CSS, оптимизация TTFB и кеширования" }
        };
    }
}
