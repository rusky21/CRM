using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Desktop.ViewModels;

public partial class FinancesViewModel : ViewModelBase
{
    private readonly IOrderService _orderService;
    private readonly IDatabaseBackupService _backupService;
    private readonly Action<int> _navigateToEdit;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private bool _isBackingUp;

    [ObservableProperty]
    private string? _backupMessage;

    [ObservableProperty]
    private string? _lastBackupPath;

    [ObservableProperty]
    private decimal _monthRevenue;

    [ObservableProperty]
    private decimal _totalRevenue;

    [ObservableProperty]
    private decimal _activeContractsSum;

    [ObservableProperty]
    private decimal _totalReceivables;

    [ObservableProperty]
    private string _dbPath = string.Empty;

    public ObservableCollection<Order> Debtors { get; } = new();
    public ObservableCollection<Payment> RecentPayments { get; } = new();

    public FinancesViewModel(
        IOrderService orderService,
        IDatabaseBackupService backupService,
        Action<int> navigateToEdit)
    {
        _orderService = orderService;
        _backupService = backupService;
        _navigateToEdit = navigateToEdit;
    }

    public async Task InitializeAsync()
    {
        DbPath = _backupService.GetDatabasePath();
        await LoadFinancialsAsync();
    }

    [RelayCommand]
    public async Task LoadFinancialsAsync()
    {
        IsLoading = true;
        try
        {
            var orders = await _orderService.GetOrdersSummaryAsync();

            var now = DateTime.Today;
            var startOfMonth = new DateTime(now.Year, now.Month, 1);

            // Flatten all confirmed payments
            var allPayments = orders.SelectMany(o => o.Payments)
                                    .Where(p => p.IsConfirmed)
                                    .OrderByDescending(p => p.PaymentDate)
                                    .ToList();

            TotalRevenue = allPayments.Sum(p => p.Amount);
            MonthRevenue = allPayments.Where(p => p.PaymentDate >= startOfMonth).Sum(p => p.Amount);

            var activeOrders = orders.Where(o => o.Status is OrderStatus.New or OrderStatus.InProgress or OrderStatus.Testing).ToList();
            ActiveContractsSum = activeOrders.Sum(o => o.TotalCost);

            // Debtors: active or completed orders with remaining debt
            var debtorsList = orders.Where(o => o.Status != OrderStatus.Cancelled && o.RemainingDebt > 0)
                                    .OrderByDescending(o => o.RemainingDebt)
                                    .ToList();

            TotalReceivables = debtorsList.Sum(o => o.RemainingDebt);

            Debtors.Clear();
            foreach (var debtor in debtorsList)
            {
                Debtors.Add(debtor);
            }

            RecentPayments.Clear();
            foreach (var p in allPayments.Take(30))
            {
                RecentPayments.Add(p);
            }
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    public void OpenOrder(Order? order)
    {
        if (order != null)
        {
            _navigateToEdit(order.Id);
        }
    }

    [RelayCommand]
    public async Task CreateBackupAsync()
    {
        IsBackingUp = true;
        BackupMessage = "Создание резервной копии базы данных...";
        try
        {
            string path = await _backupService.CreateBackupAsync();
            LastBackupPath = path;
            BackupMessage = $"Резервная копия успешно создана:\n{path}";
        }
        catch (Exception ex)
        {
            BackupMessage = $"Ошибка создания бэкапа: {ex.Message}";
        }
        finally
        {
            IsBackingUp = false;
        }
    }

    [RelayCommand]
    public void OpenBackupsFolder()
    {
        try
        {
            string folder = !string.IsNullOrWhiteSpace(LastBackupPath)
                ? Path.GetDirectoryName(LastBackupPath)!
                : Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Backups");

            if (!Directory.Exists(folder))
            {
                Directory.CreateDirectory(folder);
            }

            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                Process.Start("explorer.exe", folder);
            }
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
            {
                Process.Start("xdg-open", folder);
            }
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
            {
                Process.Start("open", folder);
            }
        }
        catch
        {
            // Ignore explorer opening issues
        }
    }
}
