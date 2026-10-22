using System.ComponentModel.DataAnnotations.Schema;
using StudioCRM.Core.Enums;

namespace StudioCRM.Core.Models;

public class Order
{
    public int Id { get; set; }
    public string OrderNumber { get; set; } = string.Empty;
    public int ClientId { get; set; }
    public Client? Client { get; set; }

    public string Title { get; set; } = string.Empty;
    public OrderStatus Status { get; set; } = OrderStatus.New;
    public decimal TotalCost { get; set; }

    public DateTime StartDate { get; set; } = DateTime.Today;
    public DateTime? Deadline { get; set; }

    public string? RepositoryUrl { get; set; }
    public string? DesignUrl { get; set; }
    public string? WorkBoardUrl { get; set; }
    public string? Notes { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public List<OrderItem> Items { get; set; } = new();
    public List<OrderStage> Stages { get; set; } = new();
    public List<Payment> Payments { get; set; } = new();

    [NotMapped]
    public decimal PaidAmount => Payments?.Where(p => p.IsConfirmed).Sum(p => p.Amount) ?? 0m;

    [NotMapped]
    public decimal RemainingDebt => Math.Max(0m, TotalCost - PaidAmount);

    [NotMapped]
    public double ProgressPercentage
    {
        get
        {
            if (Stages == null || Stages.Count == 0)
                return Status == OrderStatus.Completed ? 100.0 : 0.0;
            int completed = Stages.Count(s => s.Status == "Completed" || s.Status == "Завершен" || s.Status == "Done");
            return Math.Round((double)completed / Stages.Count * 100.0, 1);
        }
    }
}
