using StudioCRM.Core.Enums;
using StudioCRM.Core.Models;

namespace StudioCRM.Core.Interfaces;

public interface IOrderService
{
    Task<List<Order>> GetOrdersSummaryAsync();
    Task<Order?> GetOrderByIdWithDetailsAsync(int id);
    Task<Order> CreateOrderAsync(Order order);
    Task<Order> UpdateOrderAsync(Order order);
    Task<bool> UpdateOrderStatusAsync(int orderId, OrderStatus newStatus);
    Task<Payment> AddPaymentAsync(int orderId, Payment payment);
    Task<bool> DeleteOrderAsync(int id);
}
