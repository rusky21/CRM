using Microsoft.AspNetCore.Mvc;
using StudioCRM.Core.Interfaces;
using StudioCRM.Core.Models;

namespace StudioCRM.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ClientsController : ControllerBase
{
    private readonly IClientService _clientService;

    public ClientsController(IClientService clientService)
    {
        _clientService = clientService;
    }

    [HttpGet]
    public async Task<ActionResult<List<Client>>> GetClients()
    {
        var clients = await _clientService.GetClientsAsync();
        return Ok(clients);
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<Client>> GetClientById(int id)
    {
        var client = await _clientService.GetClientByIdAsync(id);
        if (client == null)
            return NotFound();

        return Ok(client);
    }

    [HttpPost]
    public async Task<ActionResult<Client>> AddOrUpdateClient([FromBody] Client client)
    {
        try
        {
            var saved = await _clientService.AddOrUpdateClientAsync(client);
            return Ok(saved);
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { error = ex.Message, details = ex.InnerException?.Message ?? ex.ToString() });
        }
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> DeleteClient(int id)
    {
        try
        {
            var deleted = await _clientService.DeleteClientAsync(id);
            if (!deleted)
                return NotFound();

            return NoContent();
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }
}
