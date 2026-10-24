using Microsoft.EntityFrameworkCore;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Models;
using StudioCRM.Data.Context;
using StudioCRM.Data.Seeds;

namespace StudioCRM.Data;

public static class DbInitializer
{
    public static void Initialize(StudioDbContext context)
    {
        context.Database.EnsureCreated();

        bool hasChanges = false;

        if (!context.ServiceItems.Any())
        {
            var services = ServicesSeed.GetServices();
            context.ServiceItems.AddRange(services);
            hasChanges = true;
        }

        if (!context.Clients.Any())
        {
            var demoClients = new List<Client>
            {
                new()
                {
                    Name = "ООО «ТехноПром Инжиниринг»",
                    ContactPerson = "Александр Волков",
                    Phone = "+7 (999) 123-45-67",
                    Email = "volkov@technoprom.ru",
                    Telegram = "@volkov_tech",
                    Notes = "Крупный корпоративный заказчик, промышленное оборудование. Оплата строго по безналу."
                },
                new()
                {
                    Name = "Стартап «FoodDash»",
                    ContactPerson = "Елена Смирнова",
                    Phone = "+7 (916) 456-78-90",
                    Email = "elena@fooddash.io",
                    Telegram = "@elena_fooddash",
                    Notes = "Быстрорастущий стартап доставки еды. Нужны быстрые итерации."
                },
                new()
                {
                    Name = "Сеть клиник «Медикус»",
                    ContactPerson = "Дмитрий Соколов",
                    Phone = "+7 (495) 789-01-23",
                    Email = "info@medicus-clinic.ru",
                    Telegram = "@dmitry_medicus",
                    Notes = "Медицинская сеть. Требуется соответствие 152-ФЗ и интеграция с МИС."
                },
                new()
                {
                    Name = "Финтех «CryptoPay»",
                    ContactPerson = "Артем Новиков",
                    Phone = "+7 (903) 321-65-43",
                    Email = "artem@cryptopay.global",
                    Telegram = "@artem_fintech",
                    Notes = "Платежные решения, крипто-шлюзы, высокие требования к безопасности."
                }
            };

            context.Clients.AddRange(demoClients);
            context.SaveChanges();

            // Seed demo orders for clients
            var servicesList = context.ServiceItems.ToList();
            var serviceLanding = servicesList.FirstOrDefault(s => s.Title.Contains("лендинг")) ?? servicesList[0];
            var serviceBackend = servicesList.FirstOrDefault(s => s.Title.Contains("Backend")) ?? servicesList[1];
            var serviceMobile = servicesList.FirstOrDefault(s => s.Title.Contains("Flutter")) ?? servicesList[2];
            var serviceFigma = servicesList.FirstOrDefault(s => s.Title.Contains("Figma")) ?? servicesList[3];
            var serviceDevOps = servicesList.FirstOrDefault(s => s.Title.Contains("CI/CD")) ?? servicesList[4];

            var order1 = new Order
            {
                OrderNumber = "ORD-2026-001",
                ClientId = demoClients[0].Id,
                Title = "Редизайн и разработка корпоративного портала",
                Status = OrderStatus.InProgress,
                StartDate = DateTime.Today.AddDays(-14),
                Deadline = DateTime.Today.AddDays(20),
                RepositoryUrl = "https://github.com/studiocrm/technoprom-portal",
                DesignUrl = "https://figma.com/file/technoprom-portal-v2",
                WorkBoardUrl = "https://trello.com/b/technoprom-board",
                Notes = "Адаптивная верстка, личный кабинет дилеров, интеграция с 1С.",
                Items = new List<OrderItem>
                {
                    new()
                    {
                        ServiceItemId = serviceFigma.Id,
                        Title = serviceFigma.Title,
                        BillingType = serviceFigma.BillingType,
                        Price = 40000,
                        Quantity = 1,
                        Subtotal = 40000,
                        IsCompleted = true
                    },
                    new()
                    {
                        ServiceItemId = serviceBackend.Id,
                        Title = serviceBackend.Title,
                        BillingType = serviceBackend.BillingType,
                        Price = 3500,
                        Quantity = 40,
                        Subtotal = 140000,
                        IsCompleted = false
                    }
                },
                Stages = new List<OrderStage>
                {
                    new() { Title = "Согласование ТЗ и дизайн-макетов", Deadline = DateTime.Today.AddDays(-5), Status = "Completed", SortOrder = 1 },
                    new() { Title = "Верстка и разработка API личного кабинета", Deadline = DateTime.Today.AddDays(10), Status = "InProgress", SortOrder = 2 },
                    new() { Title = "Интеграция с 1С и финальное тестирование", Deadline = DateTime.Today.AddDays(20), Status = "Pending", SortOrder = 3 }
                },
                Payments = new List<Payment>
                {
                    new() { Amount = 60000, PaymentType = PaymentType.BankTransfer, PaymentDate = DateTime.Today.AddDays(-12), Notes = "Аванс 33% по договору", IsConfirmed = true }
                }
            };
            order1.TotalCost = order1.Items.Sum(i => i.Subtotal);

            var order2 = new Order
            {
                OrderNumber = "ORD-2026-002",
                ClientId = demoClients[1].Id,
                Title = "Мобильное приложение доставки (MVP Flutter)",
                Status = OrderStatus.Testing,
                StartDate = DateTime.Today.AddDays(-30),
                Deadline = DateTime.Today.AddDays(5),
                RepositoryUrl = "https://github.com/studiocrm/fooddash-mobile",
                DesignUrl = "https://figma.com/file/fooddash-app",
                Notes = "MVP для тестирования в App Store и Google Play. Корзина + онлайн-оплата.",
                Items = new List<OrderItem>
                {
                    new()
                    {
                        ServiceItemId = serviceMobile.Id,
                        Title = serviceMobile.Title,
                        BillingType = serviceMobile.BillingType,
                        Price = 350000,
                        Quantity = 1,
                        Subtotal = 350000,
                        IsCompleted = true
                    },
                    new()
                    {
                        ServiceItemId = serviceDevOps.Id,
                        Title = serviceDevOps.Title,
                        BillingType = serviceDevOps.BillingType,
                        Price = 40000,
                        Quantity = 1,
                        Subtotal = 40000,
                        IsCompleted = true
                    }
                },
                Stages = new List<OrderStage>
                {
                    new() { Title = "Архитектура и верстка экранов", Deadline = DateTime.Today.AddDays(-15), Status = "Completed", SortOrder = 1 },
                    new() { Title = "Подключение API бэкенда и платежей", Deadline = DateTime.Today.AddDays(-3), Status = "Completed", SortOrder = 2 },
                    new() { Title = "Бета-тестирование в TestFlight", Deadline = DateTime.Today.AddDays(5), Status = "InProgress", SortOrder = 3 }
                },
                Payments = new List<Payment>
                {
                    new() { Amount = 195000, PaymentType = PaymentType.BankTransfer, PaymentDate = DateTime.Today.AddDays(-28), Notes = "50% предоплата", IsConfirmed = true },
                    new() { Amount = 100000, PaymentType = PaymentType.BankTransfer, PaymentDate = DateTime.Today.AddDays(-7), Notes = "Второй транш", IsConfirmed = true }
                }
            };
            order2.TotalCost = order2.Items.Sum(i => i.Subtotal);

            var order3 = new Order
            {
                OrderNumber = "ORD-2026-003",
                ClientId = demoClients[2].Id,
                Title = "Промо-лендинг для записи к врачам",
                Status = OrderStatus.Completed,
                StartDate = DateTime.Today.AddDays(-45),
                Deadline = DateTime.Today.AddDays(-10),
                Notes = "Проект сдан в срок. Высокая конверсия 8.4%.",
                Items = new List<OrderItem>
                {
                    new()
                    {
                        ServiceItemId = serviceLanding.Id,
                        Title = serviceLanding.Title,
                        BillingType = serviceLanding.BillingType,
                        Price = 45000,
                        Quantity = 1,
                        Subtotal = 45000,
                        IsCompleted = true
                    }
                },
                Stages = new List<OrderStage>
                {
                    new() { Title = "Разработка и верстка", Deadline = DateTime.Today.AddDays(-25), Status = "Completed", SortOrder = 1 },
                    new() { Title = "Сдача проекта и передача исходников", Deadline = DateTime.Today.AddDays(-10), Status = "Completed", SortOrder = 2 }
                },
                Payments = new List<Payment>
                {
                    new() { Amount = 45000, PaymentType = PaymentType.BankTransfer, PaymentDate = DateTime.Today.AddDays(-9), Notes = "Полный расчет", IsConfirmed = true }
                }
            };
            order3.TotalCost = order3.Items.Sum(i => i.Subtotal);

            var order4 = new Order
            {
                OrderNumber = "ORD-2026-004",
                ClientId = demoClients[3].Id,
                Title = "Аудит безопасности и смарт-контрактов",
                Status = OrderStatus.New,
                StartDate = DateTime.Today,
                Deadline = DateTime.Today.AddDays(14),
                Notes = "Срочный аудит перед раундом финансирования.",
                Items = new List<OrderItem>
                {
                    new()
                    {
                        Title = "Аудит информационной безопасности (PenTest)",
                        BillingType = BillingType.Fix,
                        Price = 110000,
                        Quantity = 1,
                        Subtotal = 110000,
                        IsCompleted = false
                    }
                },
                Stages = new List<OrderStage>
                {
                    new() { Title = "Подписание NDA и сбор исходников", Deadline = DateTime.Today.AddDays(2), Status = "Pending", SortOrder = 1 },
                    new() { Title = "Автоматизированное и ручное сканирование", Deadline = DateTime.Today.AddDays(8), Status = "Pending", SortOrder = 2 },
                    new() { Title = "Формирование итогового отчета", Deadline = DateTime.Today.AddDays(14), Status = "Pending", SortOrder = 3 }
                },
                Payments = new List<Payment>()
            };
            order4.TotalCost = order4.Items.Sum(i => i.Subtotal);

            context.Orders.AddRange(order1, order2, order3, order4);
            hasChanges = true;
        }

        if (hasChanges)
        {
            context.SaveChanges();
        }
    }
}
