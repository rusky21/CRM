using System;
using CommunityToolkit.Mvvm.ComponentModel;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Models;

namespace StudioCRM.Desktop.ViewModels;

public partial class OrderItemViewModel : ViewModelBase
{
    private readonly Action? _onChanged;

    public int Id { get; set; }
    public int? ServiceItemId { get; set; }

    [ObservableProperty]
    private string _title = string.Empty;

    [ObservableProperty]
    private BillingType _billingType = BillingType.Fix;

    [ObservableProperty]
    private decimal _price;

    [ObservableProperty]
    private decimal _quantity = 1m;

    [ObservableProperty]
    private decimal _subtotal;

    [ObservableProperty]
    private bool _isCompleted;

    public OrderItemViewModel(Action? onChanged = null)
    {
        _onChanged = onChanged;
        PropertyChanged += (s, e) =>
        {
            if (e.PropertyName is nameof(Price) or nameof(Quantity))
            {
                Subtotal = Price * Quantity;
                _onChanged?.Invoke();
            }
            else if (e.PropertyName == nameof(IsCompleted))
            {
                _onChanged?.Invoke();
            }
        };
    }

    public static OrderItemViewModel FromModel(OrderItem model, Action? onChanged = null)
    {
        var vm = new OrderItemViewModel(onChanged)
        {
            Id = model.Id,
            ServiceItemId = model.ServiceItemId,
            Title = model.Title,
            BillingType = model.BillingType,
            Price = model.Price,
            Quantity = model.Quantity,
            Subtotal = model.Subtotal > 0 ? model.Subtotal : model.Price * model.Quantity,
            IsCompleted = model.IsCompleted
        };
        return vm;
    }

    public OrderItem ToModel()
    {
        return new OrderItem
        {
            Id = Id,
            ServiceItemId = ServiceItemId,
            Title = Title,
            BillingType = BillingType,
            Price = Price,
            Quantity = Quantity,
            Subtotal = Price * Quantity,
            IsCompleted = IsCompleted
        };
    }
}

public partial class OrderStageViewModel : ViewModelBase
{
    private readonly Action? _onChanged;

    public int Id { get; set; }

    [ObservableProperty]
    private string _title = string.Empty;

    [ObservableProperty]
    private DateTime? _deadline;

    [ObservableProperty]
    private string _status = "Pending"; // Pending, InProgress, Completed

    [ObservableProperty]
    private int _sortOrder;

    [ObservableProperty]
    private bool _isCompleted;

    public OrderStageViewModel(Action? onChanged = null)
    {
        _onChanged = onChanged;
        PropertyChanged += (s, e) =>
        {
            if (e.PropertyName == nameof(IsCompleted))
            {
                Status = IsCompleted ? "Completed" : "Pending";
                _onChanged?.Invoke();
            }
            else if (e.PropertyName == nameof(Status))
            {
                IsCompleted = Status is "Completed" or "Завершен" or "Done";
                _onChanged?.Invoke();
            }
        };
    }

    public static OrderStageViewModel FromModel(OrderStage model, Action? onChanged = null)
    {
        return new OrderStageViewModel(onChanged)
        {
            Id = model.Id,
            Title = model.Title,
            Deadline = model.Deadline,
            Status = model.Status,
            SortOrder = model.SortOrder,
            IsCompleted = model.Status is "Completed" or "Завершен" or "Done"
        };
    }

    public OrderStage ToModel()
    {
        return new OrderStage
        {
            Id = Id,
            Title = Title,
            Deadline = Deadline,
            Status = Status,
            SortOrder = SortOrder
        };
    }
}

public partial class PaymentViewModel : ViewModelBase
{
    private readonly Action? _onChanged;

    public int Id { get; set; }

    [ObservableProperty]
    private decimal _amount;

    [ObservableProperty]
    private PaymentType _paymentType = PaymentType.BankTransfer;

    [ObservableProperty]
    private DateTime _paymentDate = DateTime.Now;

    [ObservableProperty]
    private string? _notes;

    [ObservableProperty]
    private bool _isConfirmed = true;

    public PaymentViewModel(Action? onChanged = null)
    {
        _onChanged = onChanged;
        PropertyChanged += (s, e) =>
        {
            if (e.PropertyName is nameof(Amount) or nameof(IsConfirmed))
            {
                _onChanged?.Invoke();
            }
        };
    }

    public static PaymentViewModel FromModel(Payment model, Action? onChanged = null)
    {
        return new PaymentViewModel(onChanged)
        {
            Id = model.Id,
            Amount = model.Amount,
            PaymentType = model.PaymentType,
            PaymentDate = model.PaymentDate,
            Notes = model.Notes,
            IsConfirmed = model.IsConfirmed
        };
    }

    public Payment ToModel()
    {
        return new Payment
        {
            Id = Id,
            Amount = Amount,
            PaymentType = PaymentType,
            PaymentDate = PaymentDate,
            Notes = Notes,
            IsConfirmed = IsConfirmed
        };
    }
}
