# Build stage
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# Copy project files and restore dependencies
COPY ["StudioCRM.Core/StudioCRM.Core.csproj", "StudioCRM.Core/"]
COPY ["StudioCRM.Data/StudioCRM.Data.csproj", "StudioCRM.Data/"]
COPY ["StudioCRM.Api/StudioCRM.Api.csproj", "StudioCRM.Api/"]
RUN dotnet restore "StudioCRM.Api/StudioCRM.Api.csproj"

# Copy source code and publish
COPY StudioCRM.Core/ StudioCRM.Core/
COPY StudioCRM.Data/ StudioCRM.Data/
COPY StudioCRM.Api/ StudioCRM.Api/
WORKDIR "/src/StudioCRM.Api"
RUN dotnet publish "StudioCRM.Api.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app
EXPOSE 5000
ENV ASPNETCORE_URLS=http://+:5000
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "StudioCRM.Api.dll"]
