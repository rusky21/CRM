using Microsoft.AspNetCore.Mvc;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ServicesController : ControllerBase
{
    private readonly IServiceCatalogService _catalogService;

    public ServicesController(IServiceCatalogService catalogService)
    {
        _catalogService = catalogService;
    }

    [HttpGet]
    public async Task<ActionResult<List<ServiceItem>>> GetAllServices()
    {
        var services = await _catalogService.GetAllServicesAsync();
        return Ok(services);
    }

    [HttpGet("category/{category}")]
    public async Task<ActionResult<List<ServiceItem>>> GetServicesByCategory(string category)
    {
        var services = await _catalogService.GetServicesByCategoryAsync(category);
        return Ok(services);
    }

    [HttpGet("categories")]
    public async Task<ActionResult<List<string>>> GetCategories()
    {
        var categories = await _catalogService.GetCategoriesAsync();
        return Ok(categories);
    }

    [HttpPost]
    public async Task<ActionResult<ServiceItem>> SaveService([FromBody] ServiceItem service)
    {
        var saved = await _catalogService.SaveServiceAsync(service);
        return Ok(saved);
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> DeleteService(int id)
    {
        var deleted = await _catalogService.DeleteServiceAsync(id);
        if (!deleted)
            return NotFound();

        return NoContent();
    }
}
