using System;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using StudioCRM.Core.Interfaces;
using StudioCRM.Data;
using StudioCRM.Data.Context;
using StudioCRM.Data.Services;
using StudioCRM.Desktop.Services.Http;
using StudioCRM.Desktop.Services.Proxy;
using StudioCRM.Desktop.Services.Settings;
using StudioCRM.Desktop.ViewModels;
using StudioCRM.Desktop.Views;

namespace StudioCRM.Desktop;

public partial class App : Application
{
    public IServiceProvider? Services { get; private set; }

    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        var services = new ServiceCollection();
        ConfigureServices(services);
        Services = services.BuildServiceProvider();

        // Run local SQLite initialization and seeds in background or fallback
        using (var scope = Services.CreateScope())
        {
            var dbContext = scope.ServiceProvider.GetRequiredService<StudioDbContext>();
            DbInitializer.Initialize(dbContext);
        }

        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var mainWindowViewModel = Services.GetRequiredService<MainWindowViewModel>();

            desktop.MainWindow = new MainWindow
            {
                DataContext = mainWindowViewModel
            };

            // Trigger initial async load
            _ = mainWindowViewModel.InitializeAsync();
        }

        base.OnFrameworkInitializationCompleted();
    }

    private static void ConfigureServices(IServiceCollection services)
    {
        // 1. Settings & API Client
        services.AddSingleton<ISettingsService, SettingsService>();
        services.AddSingleton<IApiClient, ApiClient>();

        // 2. Local Database & EF Core
        services.AddDbContext<StudioDbContext>(options =>
        {
            options.UseSqlite($"Data Source={StudioDbContext.DefaultDbFileName}");
        }, ServiceLifetime.Transient);

        // 3. Local implementations
        services.AddTransient<ClientService>();
        services.AddTransient<OrderService>();
        services.AddTransient<ServiceCatalogService>();
        services.AddTransient<DatabaseBackupService>();

        // 4. Remote HTTP implementations
        services.AddTransient<HttpClientService>();
        services.AddTransient<HttpOrderService>();
        services.AddTransient<HttpServiceCatalogService>();
        services.AddTransient<HttpDatabaseBackupService>();

        // 5. Proxy Services (Dynamically switches between Local and Remote based on Settings)
        services.AddTransient<IClientService, ProxyClientService>();
        services.AddTransient<IOrderService, ProxyOrderService>();
        services.AddTransient<IServiceCatalogService, ProxyServiceCatalogService>();
        services.AddTransient<IDatabaseBackupService, ProxyDatabaseBackupService>();

        // 6. ViewModels
        services.AddSingleton<MainWindowViewModel>();
        services.AddTransient<OrdersViewModel>();
        services.AddTransient<OrderEditViewModel>();
        services.AddTransient<ClientsViewModel>();
        services.AddTransient<ServicesCatalogViewModel>();
        services.AddTransient<FinancesViewModel>();
        services.AddTransient<SettingsViewModel>();
    }
}