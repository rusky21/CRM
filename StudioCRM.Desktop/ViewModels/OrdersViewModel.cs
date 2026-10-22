using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Desktop.ViewModels;

public partial class OrdersViewModel : ViewModelBase
{
    private readonly IOrderService _orderService;
    private readonly Action<int> _navigateToEdit;
    private readonly Action _navigateToCreate;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string _searchText = string.Empty;

    [ObservableProperty]
    private string _selectedStatusFilter = "Все";

    [ObservableProperty]
    private Order? _selectedOrder;

    [ObservableProperty]
    private int _totalOrdersCount;

    [ObservableProperty]
    private int _activeOrdersCount;

    [ObservableProperty]
    private decimal _activeOrdersSum;

    [ObservableProperty]
    private decimal _totalDebtSum;

    public ObservableCollection<Order> Orders { get; } = new();
    public ObservableCollection<Order> FilteredOrders { get; } = new();
    public ObservableCollection<string> StatusFilters { get; } = new()
    {
        "Все", "Новый", "В работе", "Тестирование", "Сдан", "Отменен"
    };

    public OrdersViewModel(IOrderService orderService, Action<int> navigateToEdit, Action navigateToCreate)
    {
        _orderService = orderService;
        _navigateToEdit = navigateToEdit;
        _navigateToCreate = navigateToCreate;
    }

    public async Task InitializeAsync()
    {
        await LoadOrdersAsync();
    }

    [RelayCommand]
    public async Task LoadOrdersAsync()
    {
        IsLoading = true;
        try
        {
            var list = await _orderService.GetOrdersSummaryAsync();
            Orders.Clear();
            foreach (var order in list)
            {
                Orders.Add(order);
            }

            CalculateMetrics();
            ApplyFilter();
        }
        finally
        {
            IsLoading = false;
        }
    }

    partial void OnSearchTextChanged(string value) => ApplyFilter();
    partial void OnSelectedStatusFilterChanged(string value) => ApplyFilter();

    private void CalculateMetrics()
    {
        TotalOrdersCount = Orders.Count;

        var activeOrders = Orders.Where(o => o.Status is OrderStatus.New or OrderStatus.InProgress or OrderStatus.Testing).ToList();
        ActiveOrdersCount = activeOrders.Count;
        ActiveOrdersSum = activeOrders.Sum(o => o.TotalCost);

        TotalDebtSum = Orders.Where(o => o.Status != OrderStatus.Cancelled).Sum(o => o.RemainingDebt);
    }

    private void ApplyFilter()
    {
        FilteredOrders.Clear();

        var query = Orders.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(SearchText))
        {
            string term = SearchText.Trim().ToLowerInvariant();
            query = query.Where(o =>
                (o.OrderNumber?.ToLowerInvariant().Contains(term) ?? false) ||
                (o.Title?.ToLowerInvariant().Contains(term) ?? false) ||
                (o.Client?.Name?.ToLowerInvariant().Contains(term) ?? false));
        }

        if (SelectedStatusFilter != "Все")
        {
            OrderStatus? targetStatus = SelectedStatusFilter switch
            {
                "Новый" => OrderStatus.New,
                "В работе" => OrderStatus.InProgress,
                "Тестирование" => OrderStatus.Testing,
                "Сдан" => OrderStatus.Completed,
                "Отменен" => OrderStatus.Cancelled,
                _ => null
            };

            if (targetStatus.HasValue)
            {
                query = query.Where(o => o.Status == targetStatus.Value);
            }
        }

        foreach (var order in query)
        {
            FilteredOrders.Add(order);
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
    public void CreateNewOrder()
    {
        _navigateToCreate();
    }

    public async Task QuickChangeStatusAsync(Order? order, string statusName)
    {
        if (order == null) return;

        OrderStatus newStatus = statusName switch
        {
            "New" or "Новый" => OrderStatus.New,
            "InProgress" or "В работе" => OrderStatus.InProgress,
            "Testing" or "Тестирование" => OrderStatus.Testing,
            "Completed" or "Сдан" => OrderStatus.Completed,
            "Cancelled" or "Отменен" => OrderStatus.Cancelled,
            _ => order.Status
        };

        if (order.Status != newStatus)
        {
            await _orderService.UpdateOrderStatusAsync(order.Id, newStatus);
            order.Status = newStatus;
            CalculateMetrics();
            ApplyFilter();
        }
    }
}
