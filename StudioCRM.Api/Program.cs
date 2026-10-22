using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using StudioCRM.Core.Interfaces;
using StudioCRM.Data;
using StudioCRM.Data.Context;
using StudioCRM.Data.Services;

var builder = WebApplication.CreateBuilder(args);

// 1. Database Configuration
var provider = builder.Configuration.GetValue<string>("DatabaseProvider") ?? "PostgreSql";
var pgConn = builder.Configuration.GetConnectionString("PostgreSql");
var sqliteConn = builder.Configuration.GetConnectionString("Sqlite") ?? $"Data Source={StudioDbContext.DefaultDbFileName}";

builder.Services.AddDbContext<StudioDbContext>(options =>
{
    if (provider.Equals("PostgreSql", StringComparison.OrdinalIgnoreCase) && !string.IsNullOrWhiteSpace(pgConn))
    {
        options.UseNpgsql(pgConn);
    }
    else
    {
        options.UseSqlite(sqliteConn);
    }
});

// 2. Core Business Services
builder.Services.AddScoped<IClientService, ClientService>();
builder.Services.AddScoped<IServiceCatalogService, ServiceCatalogService>();
builder.Services.AddScoped<IOrderService, OrderService>();
builder.Services.AddScoped<IDatabaseBackupService, DatabaseBackupService>();

// 3. Controllers and JSON Serialization
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.ReferenceHandler = ReferenceHandler.IgnoreCycles;
        options.JsonSerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
        options.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter());
    });

// 4. CORS Configuration for Desktop Clients
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// 5. Database Initialization / Seeding
using (var scope = app.Services.CreateScope())
{
    var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();
    try
    {
        var db = scope.ServiceProvider.GetRequiredService<StudioDbContext>();
        logger.LogInformation("Initializing database using provider: {Provider}", db.Database.ProviderName);
        DbInitializer.Initialize(db);
        logger.LogInformation("Database initialized and verified.");
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Database auto-initialization error: {Message}", ex.Message);
    }
}

app.UseCors();
app.MapControllers();

app.Run();

// Make Program public for integration testing
public partial class Program { }
