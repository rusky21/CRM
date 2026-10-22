using Microsoft.AspNetCore.Mvc;
using StudioCRM.Core.Enums;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class OrdersController : ControllerBase
{
    private readonly IOrderService _orderService;

    public OrdersController(IOrderService orderService)
    {
        _orderService = orderService;
    }

    [HttpGet("summary")]
    public async Task<ActionResult<List<Order>>> GetOrdersSummary()
    {
        var orders = await _orderService.GetOrdersSummaryAsync();
        return Ok(orders);
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<Order>> GetOrderById(int id)
    {
        var order = await _orderService.GetOrderByIdWithDetailsAsync(id);
        if (order == null)
            return NotFound();

        return Ok(order);
    }

    [HttpPost]
    public async Task<ActionResult<Order>> CreateOrder([FromBody] Order order)
    {
        var created = await _orderService.CreateOrderAsync(order);
        return CreatedAtAction(nameof(GetOrderById), new { id = created.Id }, created);
    }

    [HttpPut("{id:int}")]
    public async Task<ActionResult<Order>> UpdateOrder(int id, [FromBody] Order order)
    {
        order.Id = id;
        try
        {
            var updated = await _orderService.UpdateOrderAsync(order);
            return Ok(updated);
        }
        catch (InvalidOperationException ex)
        {
            return NotFound(ex.Message);
        }
    }

    [HttpPatch("{id:int}/status")]
    public async Task<IActionResult> UpdateOrderStatus(int id, [FromBody] UpdateStatusRequest request)
    {
        var result = await _orderService.UpdateOrderStatusAsync(id, request.Status);
        if (!result)
            return NotFound();

        return NoContent();
    }

    [HttpPost("{id:int}/payments")]
    public async Task<ActionResult<Payment>> AddPayment(int id, [FromBody] Payment payment)
    {
        var created = await _orderService.AddPaymentAsync(id, payment);
        return Ok(created);
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> DeleteOrder(int id)
    {
        var deleted = await _orderService.DeleteOrderAsync(id);
        if (!deleted)
            return NotFound();

        return NoContent();
    }
}

public class UpdateStatusRequest
{
    public OrderStatus Status { get; set; }
}
