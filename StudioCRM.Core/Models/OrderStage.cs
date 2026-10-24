namespace StudioCRM.Core.Models;

public class OrderStage
{
    public int Id { get; set; }
    public int OrderId { get; set; }
    public Order? Order { get; set; }

    public string Title { get; set; } = string.Empty;
    public DateTime? Deadline { get; set; }
    public string Status { get; set; } = "Pending"; // Pending, InProgress, Completed
    public int SortOrder { get; set; }
}
