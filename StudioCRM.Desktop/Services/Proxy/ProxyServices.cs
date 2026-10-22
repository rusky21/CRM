using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;
using StudioCRM.Data.Services;
using StudioCRM.Desktop.Services.Http;
using StudioCRM.Desktop.Services.Settings;

namespace StudioCRM.Desktop.Services.Proxy;

public class ProxyOrderService : IOrderService
{
    private readonly ISettingsService _settings;
    private readonly OrderService _local;
    private readonly HttpOrderService _remote;

    public ProxyOrderService(ISettingsService settings, OrderService local, HttpOrderService remote)
    {
        _settings = settings;
        _local = local;
        _remote = remote;
    }

    private IOrderService Active => _settings.CurrentConfig.Mode == StorageMode.Remote ? _remote : _local;

    public Task<List<Order>> GetOrdersSummaryAsync() => Active.GetOrdersSummaryAsync();
    public Task<Order?> GetOrderByIdWithDetailsAsync(int id) => Active.GetOrderByIdWithDetailsAsync(id);
    public Task<Order> CreateOrderAsync(Order order) => Active.CreateOrderAsync(order);
    public Task<Order> UpdateOrderAsync(Order order) => Active.UpdateOrderAsync(order);
    public Task<bool> UpdateOrderStatusAsync(int orderId, OrderStatus newStatus) => Active.UpdateOrderStatusAsync(orderId, newStatus);
    public Task<Payment> AddPaymentAsync(int orderId, Payment payment) => Active.AddPaymentAsync(orderId, payment);
    public Task<bool> DeleteOrderAsync(int id) => Active.DeleteOrderAsync(id);
}

public class ProxyClientService : IClientService
{
    private readonly ISettingsService _settings;
    private readonly ClientService _local;
    private readonly HttpClientService _remote;

    public ProxyClientService(ISettingsService settings, ClientService local, HttpClientService remote)
    {
        _settings = settings;
        _local = local;
        _remote = remote;
    }

    private IClientService Active => _settings.CurrentConfig.Mode == StorageMode.Remote ? _remote : _local;

    public Task<List<Client>> GetClientsAsync() => Active.GetClientsAsync();
    public Task<Client?> GetClientByIdAsync(int id) => Active.GetClientByIdAsync(id);
    public Task<Client> AddOrUpdateClientAsync(Client client) => Active.AddOrUpdateClientAsync(client);
    public Task<bool> DeleteClientAsync(int id) => Active.DeleteClientAsync(id);
}

public class ProxyServiceCatalogService : IServiceCatalogService
{
    private readonly ISettingsService _settings;
    private readonly ServiceCatalogService _local;
    private readonly HttpServiceCatalogService _remote;

    public ProxyServiceCatalogService(ISettingsService settings, ServiceCatalogService local, HttpServiceCatalogService remote)
    {
        _settings = settings;
        _local = local;
        _remote = remote;
    }

    private IServiceCatalogService Active => _settings.CurrentConfig.Mode == StorageMode.Remote ? _remote : _local;

    public Task<List<ServiceItem>> GetAllServicesAsync() => Active.GetAllServicesAsync();
    public Task<List<ServiceItem>> GetServicesByCategoryAsync(string? category = null) => Active.GetServicesByCategoryAsync(category);
    public Task<List<string>> GetCategoriesAsync() => Active.GetCategoriesAsync();
    public Task<ServiceItem> SaveServiceAsync(ServiceItem service) => Active.SaveServiceAsync(service);
    public Task<bool> DeleteServiceAsync(int id) => Active.DeleteServiceAsync(id);
}

public class ProxyDatabaseBackupService : IDatabaseBackupService
{
    private readonly ISettingsService _settings;
    private readonly DatabaseBackupService _local;
    private readonly HttpDatabaseBackupService _remote;

    public ProxyDatabaseBackupService(ISettingsService settings, DatabaseBackupService local, HttpDatabaseBackupService remote)
    {
        _settings = settings;
        _local = local;
        _remote = remote;
    }

    private IDatabaseBackupService Active => _settings.CurrentConfig.Mode == StorageMode.Remote ? _remote : _local;

    public string GetDatabasePath() => Active.GetDatabasePath();
    public Task<string> CreateBackupAsync(string? targetDirectory = null) => Active.CreateBackupAsync(targetDirectory);
}
