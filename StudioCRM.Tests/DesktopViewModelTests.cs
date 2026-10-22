using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Models;
using StudioCRM.Data;
using StudioCRM.Data.Context;
using StudioCRM.Data.Services;
using StudioCRM.Desktop.ViewModels;
using Xunit;

namespace StudioCRM.Tests;

public class DesktopViewModelTests : IDisposable
{
    private readonly SqliteConnection _connection;
    private readonly StudioDbContext _context;
    private readonly ClientService _clientService;
    private readonly OrderService _orderService;
    private readonly ServiceCatalogService _catalogService;

    public DesktopViewModelTests()
    {
        _connection = new SqliteConnection("DataSource=:memory:");
        _connection.Open();

        var options = new DbContextOptionsBuilder<StudioDbContext>()
            .UseSqlite(_connection)
            .Options;

        _context = new StudioDbContext(options);
        _context.Database.EnsureCreated();
        DbInitializer.Initialize(_context);

        _clientService = new ClientService(_context);
        _orderService = new OrderService(_context);
        _catalogService = new ServiceCatalogService(_context);
    }

    public void Dispose()
    {
        _context.Dispose();
        _connection.Dispose();
    }

    [Fact]
    public async Task OrderEditViewModel_NewOrder_InitializesWithDefaults()
    {
        var vm = new OrderEditViewModel(_orderService, _clientService, _catalogService, () => { });
        await vm.InitializeAsync();

        Assert.Equal(0, vm.OrderId);
        Assert.Equal(OrderStatus.New, vm.Status);
        Assert.Equal(0m, vm.TotalCost);
        Assert.Equal(0m, vm.PaidAmount);
        Assert.Equal(0m, vm.RemainingDebt);
        Assert.NotEmpty(vm.AvailableServices);
    }

    [Fact]
    public async Task OrderEditViewModel_ManualCostAndPayments_RecalculatesDebt()
    {
        var vm = new OrderEditViewModel(_orderService, _clientService, _catalogService, () => { });
        await vm.InitializeAsync();

        // 1. Set manual project cost
        vm.TotalCost = 200000m;
        Assert.Equal(200000m, vm.RemainingDebt);

        // 2. Add payment
        vm.NewPaymentAmount = 75000m;
        vm.NewPaymentType = PaymentType.BankTransfer;
        vm.AddPaymentCommand.Execute(null);

        Assert.Single(vm.Payments);
        Assert.Equal(75000m, vm.PaidAmount);
        Assert.Equal(125000m, vm.RemainingDebt);
    }

    [Fact]
    public async Task OrderEditViewModel_AddCatalogItemAndCalculate_Works()
    {
        var vm = new OrderEditViewModel(_orderService, _clientService, _catalogService, () => { });
        await vm.InitializeAsync();

        var service = vm.AvailableServices.First();
        vm.SelectedCatalogService = service;
        vm.AddServiceFromCatalogCommand.Execute(null);

        Assert.Single(vm.Items);
        Assert.Equal(service.Title, vm.Items.First().Title);
        Assert.True(vm.TotalCost > 0);

        // Add custom item
        vm.Items.Add(new OrderItemViewModel(vm.RecalculateTotals)
        {
            Title = "Дополнительная доработка",
            Price = 20000m,
            Quantity = 2m
        });

        vm.CalculateCostFromItemsCommand.Execute(null);
        var expectedTotal = service.DefaultPrice + (20000m * 2m);
        Assert.Equal(expectedTotal, vm.TotalCost);
    }

    [Fact]
    public async Task OrderEditViewModel_QuickClientCreation_AddsAndSelectsClient()
    {
        var vm = new OrderEditViewModel(_orderService, _clientService, _catalogService, () => { });
        await vm.InitializeAsync();

        vm.QuickClientName = "Быстрый Клиент ООО";
        vm.QuickClientPhone = "+7 999 123-45-67";
        vm.QuickClientTelegram = "@quick_client";

        await vm.CreateQuickClientCommand.ExecuteAsync(null);

        Assert.NotNull(vm.SelectedClient);
        Assert.Equal("Быстрый Клиент ООО", vm.SelectedClient.Name);
        Assert.Contains(vm.AvailableClients, c => c.Name == "Быстрый Клиент ООО");
    }

    [Fact]
    public async Task OrderEditViewModel_Stages_UpdatesProgress()
    {
        var vm = new OrderEditViewModel(_orderService, _clientService, _catalogService, () => { });
        await vm.InitializeAsync();

        vm.Stages.Clear();
        var stage1 = new OrderStageViewModel(vm.RecalculateTotals) { Title = "Этап 1", IsCompleted = false };
        var stage2 = new OrderStageViewModel(vm.RecalculateTotals) { Title = "Этап 2", IsCompleted = false };
        vm.Stages.Add(stage1);
        vm.Stages.Add(stage2);

        Assert.Equal(0, vm.ProgressPercentage);

        stage1.IsCompleted = true;
        Assert.Equal(50, vm.ProgressPercentage);

        stage2.IsCompleted = true;
        Assert.Equal(100, vm.ProgressPercentage);
    }
}
