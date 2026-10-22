using Microsoft.EntityFrameworkCore;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;
using StudioCRM.Data.Context;

namespace StudioCRM.Data.Services;

public class OrderService : IOrderService
{
    private readonly IDbContextFactory<StudioDbContext>? _contextFactory;
    private readonly StudioDbContext _context;

    public OrderService(StudioDbContext context, IDbContextFactory<StudioDbContext>? contextFactory = null)
    {
        _context = context;
        _contextFactory = contextFactory;
    }

    public async Task<List<Order>> GetOrdersSummaryAsync()
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        return await context.Orders
            .AsNoTracking()
            .Include(o => o.Client)
            .Include(o => o.Items)
            .Include(o => o.Stages)
            .Include(o => o.Payments)
            .OrderByDescending(o => o.CreatedAt)
            .ToListAsync();
    }

    public async Task<Order?> GetOrderByIdWithDetailsAsync(int id)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        return await context.Orders
            .AsNoTracking()
            .Include(o => o.Client)
            .Include(o => o.Items)
                .ThenInclude(i => i.ServiceItem)
            .Include(o => o.Stages.OrderBy(s => s.SortOrder))
            .Include(o => o.Payments.OrderByDescending(p => p.PaymentDate))
            .FirstOrDefaultAsync(o => o.Id == id);
    }

    public async Task<Order> CreateOrderAsync(Order order)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        if (string.IsNullOrWhiteSpace(order.OrderNumber))
        {
            int year = DateTime.Today.Year;
            int countThisYear = await context.Orders.CountAsync(o => o.CreatedAt.Year == year);
            order.OrderNumber = $"ORD-{year}-{(countThisYear + 1):D3}";
        }

        order.CreatedAt = DateTime.UtcNow;

        foreach (var item in order.Items)
        {
            item.Subtotal = item.Price * item.Quantity;
        }
        if (order.TotalCost <= 0)
        {
            order.TotalCost = order.Items.Sum(i => i.Subtotal);
        }

        // Ensure navigation references don't attempt to re-insert existing client
        if (order.ClientId > 0)
        {
            order.Client = null;
        }

        // Reset child IDs if new
        foreach (var item in order.Items)
        {
            if (item.Id < 0) item.Id = 0;
            item.ServiceItem = null;
        }
        foreach (var stage in order.Stages)
        {
            if (stage.Id < 0) stage.Id = 0;
        }
        foreach (var payment in order.Payments)
        {
            if (payment.Id < 0) payment.Id = 0;
        }

        context.Orders.Add(order);
        await context.SaveChangesAsync();

        return order;
    }

    public async Task<Order> UpdateOrderAsync(Order order)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        var existingOrder = await context.Orders
            .Include(o => o.Items)
            .Include(o => o.Stages)
            .Include(o => o.Payments)
            .FirstOrDefaultAsync(o => o.Id == order.Id);

        if (existingOrder == null)
        {
            throw new InvalidOperationException($"Заказ с ID {order.Id} не найден.");
        }

        // Update scalar properties
        existingOrder.Title = order.Title;
        existingOrder.ClientId = order.ClientId;
        existingOrder.Status = order.Status;
        existingOrder.StartDate = order.StartDate;
        existingOrder.Deadline = order.Deadline;
        existingOrder.RepositoryUrl = order.RepositoryUrl;
        existingOrder.DesignUrl = order.DesignUrl;
        existingOrder.WorkBoardUrl = order.WorkBoardUrl;
        existingOrder.Notes = order.Notes;

        // Synchronize Items
        var updatedItemIds = order.Items.Where(i => i.Id > 0).Select(i => i.Id).ToHashSet();
        var itemsToRemove = existingOrder.Items.Where(i => !updatedItemIds.Contains(i.Id)).ToList();
        foreach (var item in itemsToRemove)
        {
            context.OrderItems.Remove(item);
        }

        foreach (var item in order.Items)
        {
            item.Subtotal = item.Price * item.Quantity;
            if (item.Id <= 0)
            {
                existingOrder.Items.Add(new OrderItem
                {
                    OrderId = existingOrder.Id,
                    ServiceItemId = item.ServiceItemId,
                    Title = item.Title,
                    BillingType = item.BillingType,
                    Price = item.Price,
                    Quantity = item.Quantity,
                    Subtotal = item.Subtotal,
                    IsCompleted = item.IsCompleted
                });
            }
            else
            {
                var existingItem = existingOrder.Items.FirstOrDefault(i => i.Id == item.Id);
                if (existingItem != null)
                {
                    existingItem.ServiceItemId = item.ServiceItemId;
                    existingItem.Title = item.Title;
                    existingItem.BillingType = item.BillingType;
                    existingItem.Price = item.Price;
                    existingItem.Quantity = item.Quantity;
                    existingItem.Subtotal = item.Subtotal;
                    existingItem.IsCompleted = item.IsCompleted;
                }
            }
        }

        // Synchronize Stages
        var updatedStageIds = order.Stages.Where(s => s.Id > 0).Select(s => s.Id).ToHashSet();
        var stagesToRemove = existingOrder.Stages.Where(s => !updatedStageIds.Contains(s.Id)).ToList();
        foreach (var stage in stagesToRemove)
        {
            context.OrderStages.Remove(stage);
        }

        foreach (var stage in order.Stages)
        {
            if (stage.Id <= 0)
            {
                existingOrder.Stages.Add(new OrderStage
                {
                    OrderId = existingOrder.Id,
                    Title = stage.Title,
                    Deadline = stage.Deadline,
                    Status = stage.Status,
                    SortOrder = stage.SortOrder
                });
            }
            else
            {
                var existingStage = existingOrder.Stages.FirstOrDefault(s => s.Id == stage.Id);
                if (existingStage != null)
                {
                    existingStage.Title = stage.Title;
                    existingStage.Deadline = stage.Deadline;
                    existingStage.Status = stage.Status;
                    existingStage.SortOrder = stage.SortOrder;
                }
            }
        }

        // Synchronize Payments
        var updatedPaymentIds = order.Payments.Where(p => p.Id > 0).Select(p => p.Id).ToHashSet();
        var paymentsToRemove = existingOrder.Payments.Where(p => !updatedPaymentIds.Contains(p.Id)).ToList();
        foreach (var payment in paymentsToRemove)
        {
            context.Payments.Remove(payment);
        }

        foreach (var payment in order.Payments)
        {
            if (payment.Id <= 0)
            {
                existingOrder.Payments.Add(new Payment
                {
                    OrderId = existingOrder.Id,
                    Amount = payment.Amount,
                    PaymentType = payment.PaymentType,
                    PaymentDate = payment.PaymentDate,
                    Notes = payment.Notes,
                    IsConfirmed = payment.IsConfirmed
                });
            }
            else
            {
                var existingPayment = existingOrder.Payments.FirstOrDefault(p => p.Id == payment.Id);
                if (existingPayment != null)
                {
                    existingPayment.Amount = payment.Amount;
                    existingPayment.PaymentType = payment.PaymentType;
                    existingPayment.PaymentDate = payment.PaymentDate;
                    existingPayment.Notes = payment.Notes;
                    existingPayment.IsConfirmed = payment.IsConfirmed;
                }
            }
        }

        existingOrder.TotalCost = order.TotalCost > 0
            ? order.TotalCost
            : existingOrder.Items.Sum(i => i.Subtotal);

        await context.SaveChangesAsync();
        return existingOrder;
    }

    public async Task<bool> UpdateOrderStatusAsync(int orderId, OrderStatus newStatus)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        var order = await context.Orders.FindAsync(orderId);
        if (order == null)
            return false;

        order.Status = newStatus;
        await context.SaveChangesAsync();
        return true;
    }

    public async Task<Payment> AddPaymentAsync(int orderId, Payment payment)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        payment.OrderId = orderId;
        context.Payments.Add(payment);
        await context.SaveChangesAsync();
        return payment;
    }

    public async Task<bool> DeleteOrderAsync(int id)
    {
        await using var ctx = _contextFactory != null ? await _contextFactory.CreateDbContextAsync() : null;
        var context = ctx ?? _context;

        var order = await context.Orders
            .Include(o => o.Items)
            .Include(o => o.Stages)
            .Include(o => o.Payments)
            .FirstOrDefaultAsync(o => o.Id == id);

        if (order == null)
            return false;

        context.Orders.Remove(order);
        await context.SaveChangesAsync();
        return true;
    }
}
