using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Models;
using StudioCRM.Data;
using StudioCRM.Data.Context;
using StudioCRM.Data.Services;
using Xunit;

namespace StudioCRM.Tests;

public class ServicesIntegrationTests : IDisposable
{
    private readonly SqliteConnection _connection;
    private readonly StudioDbContext _context;

    public ServicesIntegrationTests()
    {
        _connection = new SqliteConnection("DataSource=:memory:");
        _connection.Open();

        var options = new DbContextOptionsBuilder<StudioDbContext>()
            .UseSqlite(_connection)
            .Options;

        _context = new StudioDbContext(options);
        _context.Database.EnsureCreated();
    }

    public void Dispose()
    {
        _context.Dispose();
        _connection.Dispose();
    }

    [Fact]
    public void DbInitializer_SeedsInitialDataCorrectly()
    {
        // Act
        DbInitializer.Initialize(_context);

        // Assert
        Assert.True(_context.ServiceItems.Any(), "Услуги должны быть созданы");
        Assert.True(_context.Clients.Any(), "Демо-клиенты должны быть созданы");
        Assert.True(_context.Orders.Any(), "Демо-заказы должны быть созданы");
    }

    [Fact]
    public async Task ClientService_CrudOperations_WorkAsExpected()
    {
        var service = new ClientService(_context);

        // Create
        var newClient = new Client
        {
            Name = "ООО «ТестСофт»",
            ContactPerson = "Иван Петров",
            Phone = "+7 (900) 111-22-33",
            Email = "ivan@testsoft.ru",
            Telegram = "@ivan_test"
        };
        var created = await service.AddOrUpdateClientAsync(newClient);
        Assert.True(created.Id > 0);

        // Read
        var allClients = await service.GetClientsAsync();
        Assert.Contains(allClients, c => c.Id == created.Id);

        // Update
        created.ContactPerson = "Иван Сидоров";
        await service.AddOrUpdateClientAsync(created);
        var updated = await service.GetClientByIdAsync(created.Id);
        Assert.Equal("Иван Сидоров", updated?.ContactPerson);

        // Delete
        var deleteResult = await service.DeleteClientAsync(created.Id);
        Assert.True(deleteResult);
        var deleted = await service.GetClientByIdAsync(created.Id);
        Assert.Null(deleted);
    }

    [Fact]
    public async Task OrderService_CreateAndUpdateStatus_WorksAsExpected()
    {
        var clientService = new ClientService(_context);
        var client = await clientService.AddOrUpdateClientAsync(new Client { Name = "Заказчик Тест" });

        var orderService = new OrderService(_context);
        var order = new Order
        {
            ClientId = client.Id,
            Title = "Разработка портала",
            Status = OrderStatus.New,
            Items = new List<OrderItem>
            {
                new() { Title = "Бэкенд", Price = 100000m, Quantity = 1m }
            }
        };

        var created = await orderService.CreateOrderAsync(order);
        Assert.True(created.Id > 0);
        Assert.StartsWith("ORD-", created.OrderNumber);
        Assert.Equal(100000m, created.TotalCost);

        // Update status
        var statusUpdated = await orderService.UpdateOrderStatusAsync(created.Id, OrderStatus.InProgress);
        Assert.True(statusUpdated);

        var refreshed = await orderService.GetOrderByIdWithDetailsAsync(created.Id);
        Assert.NotNull(refreshed);
        Assert.Equal(OrderStatus.InProgress, refreshed.Status);

        // Add payment
        var payment = await orderService.AddPaymentAsync(created.Id, new Payment
        {
            Amount = 50000m,
            PaymentType = PaymentType.BankTransfer,
            IsConfirmed = true
        });
        Assert.True(payment.Id > 0);

        var withPayment = await orderService.GetOrderByIdWithDetailsAsync(created.Id);
        Assert.Equal(50000m, withPayment?.PaidAmount);
        Assert.Equal(50000m, withPayment?.RemainingDebt);
    }

    [Fact]
    public async Task ServiceCatalogService_SaveAndSoftDelete_WorksAsExpected()
    {
        var catalogService = new ServiceCatalogService(_context);

        var service = new ServiceItem
        {
            Category = "Тестирование QA",
            Title = "Нагрузочное тестирование",
            BillingType = BillingType.Hourly,
            DefaultPrice = 3000m,
            Unit = "час"
        };

        var saved = await catalogService.SaveServiceAsync(service);
        Assert.True(saved.Id > 0);

        var activeServices = await catalogService.GetAllServicesAsync();
        Assert.Contains(activeServices, s => s.Id == saved.Id);

        // Soft delete
        var deleted = await catalogService.DeleteServiceAsync(saved.Id);
        Assert.True(deleted);

        var activeAfterDelete = await catalogService.GetAllServicesAsync();
        Assert.DoesNotContain(activeAfterDelete, s => s.Id == saved.Id);
    }
}
