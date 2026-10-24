using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using StudioCRM.Data.Context;

namespace StudioCRM.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class HealthController : ControllerBase
{
    private readonly StudioDbContext _dbContext;

    public HealthController(StudioDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    [HttpGet]
    public async Task<IActionResult> CheckHealthAsync()
    {
        bool canConnect = false;
        try
        {
            canConnect = await _dbContext.Database.CanConnectAsync();
        }
        catch
        {
            canConnect = false;
        }

        return Ok(new
        {
            Status = "OK",
            ServerTime = DateTime.UtcNow,
            DatabaseProvider = _dbContext.Database.ProviderName,
            DatabaseConnected = canConnect
        });
    }
}
