using Microsoft.EntityFrameworkCore;
using StudioCRM.Core.Models;

namespace StudioCRM.Data.Context;

public class StudioDbContext : DbContext
{
    public const string DefaultDbFileName = "studiocrm.db";

    public DbSet<Client> Clients => Set<Client>();
    public DbSet<ServiceItem> ServiceItems => Set<ServiceItem>();
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<OrderItem> OrderItems => Set<OrderItem>();
    public DbSet<OrderStage> OrderStages => Set<OrderStage>();
    public DbSet<Payment> Payments => Set<Payment>();

    public StudioDbContext()
    {
    }

    public StudioDbContext(DbContextOptions<StudioDbContext> options) : base(options)
    {
    }

    protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
    {
        if (!optionsBuilder.IsConfigured)
        {
            optionsBuilder.UseSqlite($"Data Source={DefaultDbFileName}");
        }
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Client
        modelBuilder.Entity<Client>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Name).IsRequired().HasMaxLength(200);
            entity.Property(e => e.ContactPerson).HasMaxLength(150);
            entity.Property(e => e.Phone).HasMaxLength(50);
            entity.Property(e => e.Email).HasMaxLength(120);
            entity.Property(e => e.Telegram).HasMaxLength(100);

            entity.HasMany(e => e.Orders)
                  .WithOne(o => o.Client)
                  .HasForeignKey(o => o.ClientId)
                  .OnDelete(DeleteBehavior.Restrict);
        });

        // ServiceItem
        modelBuilder.Entity<ServiceItem>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Category).IsRequired().HasMaxLength(100);
            entity.Property(e => e.Title).IsRequired().HasMaxLength(250);
            entity.Property(e => e.DefaultPrice).HasPrecision(18, 2);
            entity.Property(e => e.Unit).HasMaxLength(50);
        });

        // Order
        modelBuilder.Entity<Order>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.OrderNumber).IsRequired().HasMaxLength(50);
            entity.Property(e => e.Title).IsRequired().HasMaxLength(250);
            entity.Property(e => e.TotalCost).HasPrecision(18, 2);

            entity.HasMany(o => o.Items)
                  .WithOne(i => i.Order)
                  .HasForeignKey(i => i.OrderId)
                  .OnDelete(DeleteBehavior.Cascade);

            entity.HasMany(o => o.Stages)
                  .WithOne(s => s.Order)
                  .HasForeignKey(s => s.OrderId)
                  .OnDelete(DeleteBehavior.Cascade);

            entity.HasMany(o => o.Payments)
                  .WithOne(p => p.Order)
                  .HasForeignKey(p => p.OrderId)
                  .OnDelete(DeleteBehavior.Cascade);
        });

        // OrderItem
        modelBuilder.Entity<OrderItem>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Title).IsRequired().HasMaxLength(250);
            entity.Property(e => e.Price).HasPrecision(18, 2);
            entity.Property(e => e.Quantity).HasPrecision(18, 2);
            entity.Property(e => e.Subtotal).HasPrecision(18, 2);

            entity.HasOne(e => e.ServiceItem)
                  .WithMany()
                  .HasForeignKey(e => e.ServiceItemId)
                  .OnDelete(DeleteBehavior.SetNull);
        });

        // OrderStage
        modelBuilder.Entity<OrderStage>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Title).IsRequired().HasMaxLength(250);
            entity.Property(e => e.Status).HasMaxLength(50);
        });

        // Payment
        modelBuilder.Entity<Payment>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Amount).HasPrecision(18, 2);
            entity.Property(e => e.Notes).HasMaxLength(500);
        });
    }
}
