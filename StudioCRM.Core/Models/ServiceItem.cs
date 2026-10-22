using StudioCRM.Core.Enums;

namespace StudioCRM.Core.Models;

public class ServiceItem
{
    public int Id { get; set; }
    public string Category { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public BillingType BillingType { get; set; } = BillingType.Fix;
    public decimal DefaultPrice { get; set; }
    public string Unit { get; set; } = "проект";
    public string? Description { get; set; }
    public bool IsActive { get; set; } = true;
}
