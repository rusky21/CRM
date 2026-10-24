using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using StudioCRM.Api.Controllers;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Models;
using StudioCRM.Data.Context;
using StudioCRM.Data.Services;
using Xunit;

namespace StudioCRM.Tests;

public class ApiControllersTests : IDisposable
{
    private readonly SqliteConnection _connection;
    private readonly StudioDbContext _context;
    private readonly ClientService _clientService;
    private readonly OrderService _orderService;
    private readonly ServiceCatalogService _catalogService;
    private readonly DatabaseBackupService _backupService;

    public ApiControllersTests()
    {
        _connection = new SqliteConnection("DataSource=:memory:");
        _connection.Open();

        var options = new DbContextOptionsBuilder<StudioDbContext>()
            .UseSqlite(_connection)
            .Options;

        _context = new StudioDbContext(options);
        _context.Database.EnsureCreated();

        _clientService = new ClientService(_context);
        _orderService = new OrderService(_context);
        _catalogService = new ServiceCatalogService(_context);
        _backupService = new DatabaseBackupService();
    }

    public void Dispose()
    {
        _context.Dispose();
        _connection.Dispose();
    }

    [Fact]
    public async Task HealthController_ReturnsOkWithDatabaseStatus()
    {
        var controller = new HealthController(_context);
        var result = await controller.CheckHealthAsync();

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.NotNull(okResult.Value);
    }

    [Fact]
    public async Task ClientsController_CrudOperations_ReturnExpectedHttpResults()
    {
        var controller = new ClientsController(_clientService);

        // 1. POST (Create)
        var newClient = new Client { Name = "API Заказчик", ContactPerson = "Иван", Email = "api@test.com" };
        var postResult = await controller.AddOrUpdateClient(newClient);
        var okPostResult = Assert.IsType<OkObjectResult>(postResult.Result);
        var created = Assert.IsType<Client>(okPostResult.Value);
        Assert.True(created.Id > 0);

        // 2. GET by ID (Found)
        var getResult = await controller.GetClientById(created.Id);
        var okResult = Assert.IsType<OkObjectResult>(getResult.Result);
        var fetched = Assert.IsType<Client>(okResult.Value);
        Assert.Equal("API Заказчик", fetched.Name);

        // 3. GET by ID (Not Found)
        var notFoundResult = await controller.GetClientById(99999);
        Assert.IsType<NotFoundResult>(notFoundResult.Result);

        // 4. GET All
        var getAllResult = await controller.GetClients();
        var allOk = Assert.IsType<OkObjectResult>(getAllResult.Result);
        var list = Assert.IsAssignableFrom<IEnumerable<Client>>(allOk.Value);
        Assert.Single(list);
    }

    [Fact]
    public async Task OrdersController_FullLifecycle_WorksViaController()
    {
        var client = await _clientService.AddOrUpdateClientAsync(new Client { Name = "Клиент Заказа" });
        var controller = new OrdersController(_orderService);

        // 1. POST /api/orders
        var order = new Order
        {
            ClientId = client.Id,
            Title = "API Разработка Сайта",
            TotalCost = 180000m,
            Items = new List<OrderItem>
            {
                new() { Title = "UX Дизайн", Price = 50000m, Quantity = 1m },
                new() { Title = "Верстка", Price = 70000m, Quantity = 1m }
            },
            Stages = new List<OrderStage>
            {
                new() { Title = "Этап 1: Дизайн", Status = "Pending" },
                new() { Title = "Этап 2: Верстка", Status = "Pending" }
            }
        };

        var postResult = await controller.CreateOrder(order);
        var createdResult = Assert.IsType<CreatedAtActionResult>(postResult.Result);
        var createdOrder = Assert.IsType<Order>(createdResult.Value);
        Assert.True(createdOrder.Id > 0);
        Assert.Equal(180000m, createdOrder.TotalCost);

        // 2. GET /api/orders/{id}
        var getResult = await controller.GetOrderById(createdOrder.Id);
        var okOrderResult = Assert.IsType<OkObjectResult>(getResult.Result);
        var fetchedOrder = Assert.IsType<Order>(okOrderResult.Value);
        Assert.Equal(2, fetchedOrder.Stages.Count);

        // 3. POST /api/orders/{id}/payments
        var payment = new Payment
        {
            Amount = 60000m,
            IsConfirmed = true,
            PaymentType = PaymentType.BankTransfer
        };
        var payResult = await controller.AddPayment(createdOrder.Id, payment);
        var okPayResult = Assert.IsType<OkObjectResult>(payResult.Result);
        var createdPayment = Assert.IsType<Payment>(okPayResult.Value);
        Assert.Equal(60000m, createdPayment.Amount);

        // 4. PATCH /api/orders/{id}/status
        var statusResult = await controller.UpdateOrderStatus(createdOrder.Id, new UpdateStatusRequest { Status = OrderStatus.InProgress });
        Assert.IsType<NoContentResult>(statusResult);

        // 5. DELETE /api/orders/{id}
        var deleteResult = await controller.DeleteOrder(createdOrder.Id);
        Assert.IsType<NoContentResult>(deleteResult);
    }

    [Fact]
    public async Task ServicesController_CreateGetDelete_WorksCorrectly()
    {
        var controller = new ServicesController(_catalogService);

        // 1. POST
        var service = new ServiceItem
        {
            Category = "Консалтинг",
            Title = "Аудит безопасности",
            BillingType = BillingType.Fix,
            DefaultPrice = 45000m,
            Unit = "проект"
        };
        var postResult = await controller.SaveService(service);
        var okPost = Assert.IsType<OkObjectResult>(postResult.Result);
        var saved = Assert.IsType<ServiceItem>(okPost.Value);
        Assert.True(saved.Id > 0);

        // 2. GET
        var getAllResult = await controller.GetAllServices();
        var okGet = Assert.IsType<OkObjectResult>(getAllResult.Result);
        var items = Assert.IsAssignableFrom<IEnumerable<ServiceItem>>(okGet.Value);
        Assert.Contains(items, s => s.Id == saved.Id);

        // 3. DELETE
        var deleteResult = await controller.DeleteService(saved.Id);
        Assert.IsType<NoContentResult>(deleteResult);

        // Verify soft-deleted
        var afterDeleteResult = await controller.GetAllServices();
        var okAfter = Assert.IsType<OkObjectResult>(afterDeleteResult.Result);
        var activeAfter = Assert.IsAssignableFrom<IEnumerable<ServiceItem>>(okAfter.Value);
        Assert.DoesNotContain(activeAfter, s => s.Id == saved.Id);
    }

    [Fact]
    public async Task FinancesController_ReturnsCorrectSummary()
    {
        var client = await _clientService.AddOrUpdateClientAsync(new Client { Name = "Финансовый Клиент" });
        var order = await _orderService.CreateOrderAsync(new Order
        {
            ClientId = client.Id,
            Title = "Проект Финансов",
            TotalCost = 100000m,
            Status = OrderStatus.InProgress,
            Payments = new List<Payment>
            {
                new() { Amount = 40000m, IsConfirmed = true, PaymentDate = DateTime.Today }
            }
        });

        var controller = new FinancesController(_orderService, _backupService);
        var summaryResult = await controller.GetFinancialSummary();

        var okResult = Assert.IsType<OkObjectResult>(summaryResult.Result);
        var summary = Assert.IsType<FinancialSummaryResponse>(okResult.Value);

        Assert.Equal(40000m, summary.MonthRevenue);
        Assert.Equal(40000m, summary.TotalRevenue);
        Assert.Equal(100000m, summary.ActiveContractsSum);
        Assert.Equal(60000m, summary.TotalReceivables);
        Assert.Single(summary.Debtors);
        Assert.Single(summary.RecentPayments);
    }
}
