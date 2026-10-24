using StudioCRM.Core.Enums;

namespace StudioCRM.Core.Models;

public class OrderItem
{
    public int Id { get; set; }
    public int OrderId { get; set; }
    public Order? Order { get; set; }

    public int? ServiceItemId { get; set; }
    public ServiceItem? ServiceItem { get; set; }

    public string Title { get; set; } = string.Empty;
    public BillingType BillingType { get; set; } = BillingType.Fix;
    public decimal Price { get; set; }
    public decimal Quantity { get; set; } = 1m;
    public decimal Subtotal { get; set; }
    public bool IsCompleted { get; set; }
}
