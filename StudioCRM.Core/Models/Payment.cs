using StudioCRM.Core.Enums;

namespace StudioCRM.Core.Models;

public class Payment
{
    public int Id { get; set; }
    public int OrderId { get; set; }
    public Order? Order { get; set; }

    public decimal Amount { get; set; }
    public PaymentType PaymentType { get; set; } = PaymentType.BankTransfer;
    public DateTime PaymentDate { get; set; } = DateTime.Now;
    public string? Notes { get; set; }
    public bool IsConfirmed { get; set; } = true;
}
