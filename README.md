# 🚀 StudioCRM — Система управления веб-студией и IT-проектами

[![Release](https://img.shields.io/github/v/release/rusky21/CRM?color=6366F1&label=Версия)](https://github.com/rusky21/CRM/releases/latest)
[![Platform](https://img.shields.io/badge/Платформа-Windows%20x64-34D399)](https://github.com/rusky21/CRM/releases/latest)
[![.NET](https://img.shields.io/badge/.NET-10.0-818CF8)](https://dotnet.microsoft.com/)

StudioCRM — современная кроссплатформенная CRM-система для студий заказной разработки, агентств и digital-команд с поддержкой локальной работы и синхронизации данных между несколькими устройствами.

---

## 📥 Быстрый старт: Скачать готовые программы

Готовые автономные сборки (не требуют установки .NET или сторонних зависимостей):

* 💻 **Клиент для Windows:** 👉 **[Скачать StudioCRM-Windows-x64.zip](https://github.com/rusky21/CRM/releases/download/v1.0.1/StudioCRM-Windows-x64.zip)**  
  *Распакуйте архив и запустите `StudioCRM.Desktop.exe`.*
* 🐧 **Сервер для Ubuntu / Linux:** 👉 **[Скачать StudioCRM-Server-Linux-x64.tar.gz](https://github.com/rusky21/CRM/releases/download/v1.0.1/StudioCRM-Server-Linux-x64.tar.gz)**  
  *Автономный бинарник сервера, запускается в 3 команды на любом Linux/Ubuntu VPS.*

> 💡 **Почему папки `publish` нет в файлах репозитория:** В Git по стандарту выкладывается исходный код, а все скомпилированные бинарники хранятся во вкладке **[Releases](https://github.com/rusky21/CRM/releases)**.

---

## 🔄 Настройка сервера на Ubuntu

Для сервера на Ubuntu есть два простых способа:

### Способ 1. Без Docker и без .NET (самый быстрый)
Выполните на вашем сервере Ubuntu в терминале:
```bash
# 1. Скачать готовый бинарник сервера
wget https://github.com/rusky21/CRM/releases/download/v1.0.1/StudioCRM-Server-Linux-x64.tar.gz

# 2. Распаковать архив
tar -xzf StudioCRM-Server-Linux-x64.tar.gz

# 3. Дать права на исполнение и запустить
chmod +x StudioCRM.Api
./StudioCRM.Api --urls=http://0.0.0.0:5000
```
Сервер запустится на порту `5000` и создаст локальную базу данных `studiocrm_server.db`.

### Способ 2. Через Docker Compose (с PostgreSQL для постоянной работы)
```bash
git clone https://github.com/rusky21/CRM.git
cd CRM
docker compose up -d
```
Docker автоматически поднимет базу PostgreSQL 17 и API-сервер StudioCRM с автоперезапуском при перезагрузке машины.

### 2. Подключение рабочих мест (`StudioCRM.Desktop`)
На любом клиентском компьютере:
1. Запустите `StudioCRM.Desktop.exe`.
2. Нажмите на иконку шестерёнки **«Настройки»** в боковом меню.
3. В поле **«Адрес сервера CRM»** введите IP-адрес компьютера с сервером (например, `http://192.168.1.100:5000`).
4. Нажмите кнопку **«Проверить связь»** — появится зелёный индикатор подключения.
5. Нажмите **«Сохранить»** — теперь все заказы, клиенты, платежи и сметы синхронизируются мгновенно между всеми подключенными устройствами!

> 🛡️ Если сервер временно недоступен или нет сети, десктопное приложение автоматически продолжает работать в автономном режиме с локальной базой данных SQLite.

---

## ✨ Основные возможности

* **📊 Управление проектами и заказами:**
  * Карточки заказов со статусами (*Новый*, *В работе*, *На паузе*, *Завершен*, *Отменен*).
  * Интеграция ссылок на репозиторий Git, макеты Figma и доски задач (YouTrack / Jira / Trello / Kaiten).
  * Выбор дат старта и дедлайнов с валидацией.
* **💰 Гибкое ценообразование и сметы:**
  * Произвольный ручной ввод суммы договора или автоматический расчет по смете услуг (`⚡ Рассчитать по смете`).
  * Каталог базовых услуг агентства (Frontend, Backend, Дизайн, Аналитика, SEO, QA) с ценами и единицами измерения.
  * Финансовый блок: учет оплат (безнал, карта, наличные), расчет внесенных сумм и автоматический контроль дебиторской задолженности.
* **✅ Чек-лист этапов разработки:**
  * Индивидуальные этапы с дедлайнами и отметками выполнения.
  * Расчет общего процента готовности проекта (Progress Bar).
* **👥 Клиентская база:**
  * Быстрое создание клиента прямо из формы заказа.
  * История всех заказов и контактов заказчика (Telegram, телефон, email).

---

## 🛠️ Сборка из исходного кода для разработчиков

Требования: [.NET 10.0 SDK](https://dotnet.microsoft.com/download/dotnet/10.0).

```bash
# Клонирование репозитория
git clone https://github.com/rusky21/CRM.git
cd CRM

# Запуск тестов
dotnet test

# Сборка автономного исполняемого файла Desktop
dotnet publish StudioCRM.Desktop/StudioCRM.Desktop.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o ./publish
```

---

## 📂 Структура репозитория

```
CRM/
├── StudioCRM.Core/       # Доменные модели (Order, Client, ServiceItem, Payment), интерфейсы
├── StudioCRM.Data/       # Entity Framework Core, SQLite контекст, репозитории и сервисы
├── StudioCRM.Api/        # REST API сервер (ASP.NET Core, Swagger, CORS, кросс-устройство)
├── StudioCRM.Desktop/    # Клиент на Avalonia UI (MVVM, DataGrid, графический интерфейс)
└── StudioCRM.Tests/      # Модульные и интеграционные тесты (xUnit)
```
