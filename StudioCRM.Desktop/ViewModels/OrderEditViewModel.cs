using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Desktop.ViewModels;

public partial class OrderEditViewModel : ViewModelBase
{
    private readonly IOrderService _orderService;
    private readonly IClientService _clientService;
    private readonly IServiceCatalogService _catalogService;
    private readonly Action _navigateBack;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsExistingOrder))]
    private int _orderId;

    public bool IsExistingOrder => OrderId > 0;

    [ObservableProperty]
    private string _orderNumber = string.Empty;

    [ObservableProperty]
    private string _title = string.Empty;

    [ObservableProperty]
    private OrderStatus _status = OrderStatus.New;

    [ObservableProperty]
    private DateTime _startDate = DateTime.Today;

    [ObservableProperty]
    private DateTime? _deadline = DateTime.Today.AddDays(14);

    [ObservableProperty]
    private string? _repositoryUrl;

    [ObservableProperty]
    private string? _designUrl;

    [ObservableProperty]
    private string? _workBoardUrl;

    [ObservableProperty]
    private string? _notes;

    [ObservableProperty]
    private Client? _selectedClient;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private bool _isSaving;

    [ObservableProperty]
    private string? _statusMessage;

    // Totals
    [ObservableProperty]
    private decimal _totalCost;

    [ObservableProperty]
    private decimal _paidAmount;

    [ObservableProperty]
    private decimal _remainingDebt;

    [ObservableProperty]
    private double _progressPercentage;

    // Catalog selection
    [ObservableProperty]
    private ServiceItem? _selectedCatalogService;

    // Inline quick client creation
    [ObservableProperty]
    private bool _isQuickClientOpen;

    [ObservableProperty]
    private string _quickClientName = string.Empty;

    [ObservableProperty]
    private string? _quickClientPerson;

    [ObservableProperty]
    private string? _quickClientPhone;

    [ObservableProperty]
    private string? _quickClientEmail;

    [ObservableProperty]
    private string? _quickClientTelegram;

    // Inline payment creation
    [ObservableProperty]
    private decimal _newPaymentAmount;

    [ObservableProperty]
    private PaymentType _newPaymentType = PaymentType.BankTransfer;

    [ObservableProperty]
    private string? _newPaymentNotes;

    public ObservableCollection<Client> AvailableClients { get; } = new();
    public ObservableCollection<ServiceItem> AvailableServices { get; } = new();
    public ObservableCollection<OrderItemViewModel> Items { get; } = new();
    public ObservableCollection<OrderStageViewModel> Stages { get; } = new();
    public ObservableCollection<PaymentViewModel> Payments { get; } = new();

    public Array OrderStatuses => Enum.GetValues(typeof(OrderStatus));
    public Array PaymentTypes => Enum.GetValues(typeof(PaymentType));

    public OrderEditViewModel(
        IOrderService orderService,
        IClientService clientService,
        IServiceCatalogService catalogService,
        Action navigateBack,
        int orderId = 0)
    {
        _orderService = orderService;
        _clientService = clientService;
        _catalogService = catalogService;
        _navigateBack = navigateBack;
        _orderId = orderId;
    }

    public async Task InitializeAsync()
    {
        IsLoading = true;
        try
        {
            var clients = await _clientService.GetClientsAsync();
            AvailableClients.Clear();
            foreach (var client in clients)
            {
                AvailableClients.Add(client);
            }

            var services = await _catalogService.GetAllServicesAsync();
            AvailableServices.Clear();
            foreach (var service in services)
            {
                AvailableServices.Add(service);
            }

            if (OrderId > 0)
            {
                var order = await _orderService.GetOrderByIdWithDetailsAsync(OrderId);
                if (order != null)
                {
                    OrderNumber = order.OrderNumber;
                    Title = order.Title;
                    Status = order.Status;
                    StartDate = order.StartDate;
                    Deadline = order.Deadline;
                    RepositoryUrl = order.RepositoryUrl;
                    DesignUrl = order.DesignUrl;
                    WorkBoardUrl = order.WorkBoardUrl;
                    Notes = order.Notes;
                    TotalCost = order.TotalCost > 0 ? order.TotalCost : order.Items.Sum(i => i.Subtotal);

                    SelectedClient = AvailableClients.FirstOrDefault(c => c.Id == order.ClientId);

                    Items.Clear();
                    foreach (var item in order.Items)
                    {
                        Items.Add(OrderItemViewModel.FromModel(item, RecalculateTotals));
                    }

                    Stages.Clear();
                    foreach (var stage in order.Stages)
                    {
                        Stages.Add(OrderStageViewModel.FromModel(stage, RecalculateTotals));
                    }

                    Payments.Clear();
                    foreach (var payment in order.Payments)
                    {
                        Payments.Add(PaymentViewModel.FromModel(payment, RecalculateTotals));
                    }
                }
            }
            else
            {
                // New order default
                int year = DateTime.Today.Year;
                OrderNumber = $"ORD-{year}-НОВЫЙ";
                Title = "Новый проект";
                StartDate = DateTime.Today;
                Deadline = DateTime.Today.AddDays(14);
                SelectedClient = AvailableClients.FirstOrDefault();

                // Add sample default stage
                Stages.Add(new OrderStageViewModel(RecalculateTotals)
                {
                    Title = "Согласование ТЗ и требований",
                    Deadline = DateTime.Today.AddDays(3),
                    Status = "InProgress",
                    SortOrder = 1
                });
            }

            RecalculateTotals();
        }
        finally
        {
            IsLoading = false;
        }
    }

    partial void OnTotalCostChanged(decimal value)
    {
        RemainingDebt = Math.Max(0m, value - PaidAmount);
        if (NewPaymentAmount == 0 && RemainingDebt > 0)
        {
            NewPaymentAmount = RemainingDebt;
        }
    }

    public void RecalculateTotals()
    {
        if (TotalCost == 0 && Items.Count > 0)
        {
            TotalCost = Items.Sum(i => i.Price * i.Quantity);
        }

        PaidAmount = Payments.Where(p => p.IsConfirmed).Sum(p => p.Amount);
        RemainingDebt = Math.Max(0m, TotalCost - PaidAmount);

        if (Stages.Count > 0)
        {
            int completed = Stages.Count(s => s.IsCompleted || s.Status is "Completed" or "Done" or "Завершен");
            ProgressPercentage = Math.Round((double)completed / Stages.Count * 100.0, 1);
        }
        else
        {
            ProgressPercentage = Status == OrderStatus.Completed ? 100.0 : 0.0;
        }

        // Default new payment amount to remaining debt
        if (NewPaymentAmount == 0 && RemainingDebt > 0)
        {
            NewPaymentAmount = RemainingDebt;
        }
    }

    [RelayCommand]
    public void CalculateCostFromItems()
    {
        TotalCost = Items.Sum(i => i.Price * i.Quantity);
        RecalculateTotals();
    }

    [RelayCommand]
    public void AddServiceFromCatalog()
    {
        if (SelectedCatalogService == null) return;

        var newItem = new OrderItemViewModel(RecalculateTotals)
        {
            ServiceItemId = SelectedCatalogService.Id,
            Title = SelectedCatalogService.Title,
            BillingType = SelectedCatalogService.BillingType,
            Price = SelectedCatalogService.DefaultPrice,
            Quantity = 1m,
            Subtotal = SelectedCatalogService.DefaultPrice,
            IsCompleted = false
        };

        Items.Add(newItem);
        RecalculateTotals();
    }

    [RelayCommand]
    public void AddCustomItem()
    {
        var newItem = new OrderItemViewModel(RecalculateTotals)
        {
            Title = "Индивидуальная доработка / модуль",
            BillingType = BillingType.Fix,
            Price = 10000m,
            Quantity = 1m,
            Subtotal = 10000m,
            IsCompleted = false
        };

        Items.Add(newItem);
        RecalculateTotals();
    }

    [RelayCommand]
    public void RemoveItem(OrderItemViewModel? item)
    {
        if (item != null && Items.Contains(item))
        {
            Items.Remove(item);
            RecalculateTotals();
        }
    }

    [RelayCommand]
    public void AddStage()
    {
        int nextSort = Stages.Count + 1;
        Stages.Add(new OrderStageViewModel(RecalculateTotals)
        {
            Title = $"Этап {nextSort}",
            Deadline = DateTime.Today.AddDays(7 * nextSort),
            Status = "Pending",
            SortOrder = nextSort,
            IsCompleted = false
        });
        RecalculateTotals();
    }

    [RelayCommand]
    public void RemoveStage(OrderStageViewModel? stage)
    {
        if (stage != null && Stages.Contains(stage))
        {
            Stages.Remove(stage);
            RecalculateTotals();
        }
    }

    [RelayCommand]
    public void AddPayment()
    {
        if (NewPaymentAmount <= 0) return;

        Payments.Add(new PaymentViewModel(RecalculateTotals)
        {
            Amount = NewPaymentAmount,
            PaymentType = NewPaymentType,
            PaymentDate = DateTime.Now,
            Notes = NewPaymentNotes ?? "Оплата по заказу",
            IsConfirmed = true
        });

        NewPaymentAmount = 0;
        NewPaymentNotes = null;
        RecalculateTotals();
    }

    [RelayCommand]
    public void RemovePayment(PaymentViewModel? payment)
    {
        if (payment != null && Payments.Contains(payment))
        {
            Payments.Remove(payment);
            RecalculateTotals();
        }
    }

    [RelayCommand]
    public void ToggleQuickClient()
    {
        IsQuickClientOpen = !IsQuickClientOpen;
    }

    [RelayCommand]
    public async Task CreateQuickClient()
    {
        if (string.IsNullOrWhiteSpace(QuickClientName)) return;

        var client = new Client
        {
            Name = QuickClientName.Trim(),
            ContactPerson = QuickClientPerson?.Trim(),
            Phone = QuickClientPhone?.Trim(),
            Email = QuickClientEmail?.Trim(),
            Telegram = QuickClientTelegram?.Trim(),
            CreatedAt = DateTime.Now
        };

        var created = await _clientService.AddOrUpdateClientAsync(client);
        AvailableClients.Add(created);
        SelectedClient = created;

        QuickClientName = string.Empty;
        QuickClientPerson = null;
        QuickClientPhone = null;
        QuickClientEmail = null;
        QuickClientTelegram = null;
        IsQuickClientOpen = false;
    }

    [RelayCommand]
    public async Task SaveOrderAsync()
    {
        if (SelectedClient == null)
        {
            StatusMessage = "Пожалуйста, выберите клиента для заказа.";
            return;
        }

        if (string.IsNullOrWhiteSpace(Title))
        {
            StatusMessage = "Введите название проекта.";
            return;
        }

        IsSaving = true;
        StatusMessage = "Сохранение заказа...";
        try
        {
            var order = new Order
            {
                Id = OrderId,
                OrderNumber = OrderNumber,
                ClientId = SelectedClient.Id,
                Title = Title.Trim(),
                Status = Status,
                StartDate = StartDate,
                Deadline = Deadline,
                RepositoryUrl = RepositoryUrl,
                DesignUrl = DesignUrl,
                WorkBoardUrl = WorkBoardUrl,
                Notes = Notes,
                TotalCost = TotalCost > 0 ? TotalCost : Items.Sum(i => i.Price * i.Quantity),
                Items = Items.Select(i => i.ToModel()).ToList(),
                Stages = Stages.Select(s => s.ToModel()).ToList(),
                Payments = Payments.Select(p => p.ToModel()).ToList()
            };

            if (OrderId == 0)
            {
                var created = await _orderService.CreateOrderAsync(order);
                OrderId = created.Id;
                OrderNumber = created.OrderNumber;
            }
            else
            {
                await _orderService.UpdateOrderAsync(order);
            }

            StatusMessage = "Заказ успешно сохранен!";
            await Task.Delay(400);
            _navigateBack();
        }
        catch (Exception ex)
        {
            StatusMessage = $"Ошибка сохранения: {ex.Message}";
        }
        finally
        {
            IsSaving = false;
        }
    }

    [RelayCommand]
    public async Task DeleteOrderAsync()
    {
        if (OrderId <= 0) return;

        IsSaving = true;
        try
        {
            await _orderService.DeleteOrderAsync(OrderId);
            _navigateBack();
        }
        catch (Exception ex)
        {
            StatusMessage = $"Ошибка удаления: {ex.Message}";
        }
        finally
        {
            IsSaving = false;
        }
    }

    [RelayCommand]
    public void OpenUrl(string? url)
    {
        if (string.IsNullOrWhiteSpace(url)) return;

        try
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                Process.Start(new ProcessStartInfo("cmd", $"/c start {url.Replace("&", "^&")}") { CreateNoWindow = true });
            }
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
            {
                Process.Start("xdg-open", url);
            }
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
            {
                Process.Start("open", url);
            }
        }
        catch
        {
            // Ignore browser opening failures
        }
    }

    [RelayCommand]
    public void Back()
    {
        _navigateBack();
    }
}
