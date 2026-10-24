using System;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Extensions.DependencyInjection;
using StudioCRM.Core.Interfaces;
using StudioCRM.Desktop.Services.Http;
using StudioCRM.Desktop.Services.Settings;

namespace StudioCRM.Desktop.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private readonly IServiceProvider _serviceProvider;
    private readonly ISettingsService _settingsService;

    [ObservableProperty]
    private ViewModelBase? _currentPageViewModel;

    [ObservableProperty]
    private string _currentPageTitle = "Заказы и проекты";

    [ObservableProperty]
    private bool _isOrdersSelected = true;

    [ObservableProperty]
    private bool _isClientsSelected;

    [ObservableProperty]
    private bool _isServicesSelected;

    [ObservableProperty]
    private bool _isFinancesSelected;

    [ObservableProperty]
    private bool _isSettingsSelected;

    // Sidebar connection status
    [ObservableProperty]
    private string _connectionModeText = "SQLite (Local)";

    [ObservableProperty]
    private string _connectionModeSubtext = "Локальная база данных";

    [ObservableProperty]
    private string _connectionStatusColor = "#10B981"; // Emerald for local, Indigo for remote

    public MainWindowViewModel(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
        _settingsService = serviceProvider.GetRequiredService<ISettingsService>();

        UpdateConnectionStatusDisplay();
        _settingsService.ConfigChanged += UpdateConnectionStatusDisplay;
    }

    public void UpdateConnectionStatusDisplay()
    {
        var config = _settingsService.CurrentConfig;
        if (config.Mode == StorageMode.Remote)
        {
            try
            {
                var uri = new Uri(config.ServerUrl);
                ConnectionModeText = $"Сервер: {uri.Host}:{uri.Port}";
            }
            catch
            {
                ConnectionModeText = $"Сервер: {config.ServerUrl}";
            }
            ConnectionModeSubtext = "Синхронизация активна";
            ConnectionStatusColor = "#818CF8"; // Indigo
        }
        else
        {
            ConnectionModeText = "SQLite Connected";
            ConnectionModeSubtext = "studiocrm.db • Ready";
            ConnectionStatusColor = "#10B981"; // Emerald
        }
    }

    public async Task InitializeAsync()
    {
        await NavigateToOrdersAsync();
    }

    [RelayCommand]
    public async Task NavigateToOrdersAsync()
    {
        SetNavState(orders: true);
        CurrentPageTitle = "Заказы и проекты студии";

        var vm = new OrdersViewModel(
            _serviceProvider.GetRequiredService<IOrderService>(),
            orderId => NavigateToOrderEdit(orderId),
            () => NavigateToCreateOrder());

        CurrentPageViewModel = vm;
        await vm.InitializeAsync();
    }

    [RelayCommand]
    public async Task NavigateToClientsAsync()
    {
        SetNavState(clients: true);
        CurrentPageTitle = "База клиентов и контрагентов";

        var vm = new ClientsViewModel(_serviceProvider.GetRequiredService<IClientService>());
        CurrentPageViewModel = vm;
        await vm.InitializeAsync();
    }

    [RelayCommand]
    public async Task NavigateToServicesAsync()
    {
        SetNavState(services: true);
        CurrentPageTitle = "Каталог услуг и прайс-лист";

        var vm = new ServicesCatalogViewModel(_serviceProvider.GetRequiredService<IServiceCatalogService>());
        CurrentPageViewModel = vm;
        await vm.InitializeAsync();
    }

    [RelayCommand]
    public async Task NavigateToFinancesAsync()
    {
        SetNavState(finances: true);
        CurrentPageTitle = "Финансы, дебиторка и резервное копирование";

        var vm = new FinancesViewModel(
            _serviceProvider.GetRequiredService<IOrderService>(),
            _serviceProvider.GetRequiredService<IDatabaseBackupService>(),
            orderId => NavigateToOrderEdit(orderId));

        CurrentPageViewModel = vm;
        await vm.InitializeAsync();
    }

    [RelayCommand]
    public Task NavigateToSettingsAsync()
    {
        SetNavState(settings: true);
        CurrentPageTitle = "Настройки сервера и синхронизации";

        var vm = new SettingsViewModel(
            _settingsService,
            _serviceProvider.GetRequiredService<IApiClient>(),
            () => UpdateConnectionStatusDisplay());

        CurrentPageViewModel = vm;
        return Task.CompletedTask;
    }

    [RelayCommand]
    public void NavigateToCreateOrder()
    {
        NavigateToOrderEdit(0);
    }

    public void NavigateToOrderEdit(int orderId)
    {
        SetNavState(orders: true);
        CurrentPageTitle = orderId > 0 ? "Редактирование заказа" : "Создание нового заказа";

        var vm = new OrderEditViewModel(
            _serviceProvider.GetRequiredService<IOrderService>(),
            _serviceProvider.GetRequiredService<IClientService>(),
            _serviceProvider.GetRequiredService<IServiceCatalogService>(),
            () => _ = NavigateToOrdersAsync(),
            orderId);

        CurrentPageViewModel = vm;
        _ = vm.InitializeAsync();
    }

    private void SetNavState(bool orders = false, bool clients = false, bool services = false, bool finances = false, bool settings = false)
    {
        IsOrdersSelected = orders;
        IsClientsSelected = clients;
        IsServicesSelected = services;
        IsFinancesSelected = finances;
        IsSettingsSelected = settings;
    }
}
