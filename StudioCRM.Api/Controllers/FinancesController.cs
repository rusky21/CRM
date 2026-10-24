using Microsoft.AspNetCore.Mvc;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class FinancesController : ControllerBase
{
    private readonly IOrderService _orderService;
    private readonly IDatabaseBackupService _backupService;

    public FinancesController(IOrderService orderService, IDatabaseBackupService backupService)
    {
        _orderService = orderService;
        _backupService = backupService;
    }

    [HttpGet("summary")]
    public async Task<ActionResult<FinancialSummaryResponse>> GetFinancialSummary()
    {
        var orders = await _orderService.GetOrdersSummaryAsync();

        var now = DateTime.Today;
        var startOfMonth = new DateTime(now.Year, now.Month, 1);

        var allPayments = orders.SelectMany(o => o.Payments)
                                .Where(p => p.IsConfirmed)
                                .OrderByDescending(p => p.PaymentDate)
                                .ToList();

        var totalRevenue = allPayments.Sum(p => p.Amount);
        var monthRevenue = allPayments.Where(p => p.PaymentDate >= startOfMonth).Sum(p => p.Amount);

        var activeOrders = orders.Where(o => o.Status is OrderStatus.New or OrderStatus.InProgress or OrderStatus.Testing).ToList();
        var activeContractsSum = activeOrders.Sum(o => o.TotalCost);

        var debtorsList = orders.Where(o => o.Status != OrderStatus.Cancelled && o.RemainingDebt > 0)
                                .OrderByDescending(o => o.RemainingDebt)
                                .ToList();

        var totalReceivables = debtorsList.Sum(o => o.RemainingDebt);

        return Ok(new FinancialSummaryResponse
        {
            MonthRevenue = monthRevenue,
            TotalRevenue = totalRevenue,
            ActiveContractsSum = activeContractsSum,
            TotalReceivables = totalReceivables,
            Debtors = debtorsList,
            RecentPayments = allPayments.Take(30).ToList()
        });
    }

    [HttpPost("backup")]
    public async Task<IActionResult> CreateBackup()
    {
        try
        {
            var path = await _backupService.CreateBackupAsync();
            return Ok(new { BackupPath = path, CreatedAt = DateTime.UtcNow });
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { Error = ex.Message });
        }
    }
}

public class FinancialSummaryResponse
{
    public decimal MonthRevenue { get; set; }
    public decimal TotalRevenue { get; set; }
    public decimal ActiveContractsSum { get; set; }
    public decimal TotalReceivables { get; set; }
    public List<Order> Debtors { get; set; } = new();
    public List<Payment> RecentPayments { get; set; } = new();
}
