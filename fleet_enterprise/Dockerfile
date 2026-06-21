# syntax=docker/dockerfile:1

FROM mcr.microsoft.com/dotnet/sdk:10.0-alpine AS base

FROM base AS deps
WORKDIR /source
# Copy the entire project directory into the container to ensure all referenced
# projects and files are available for `dotnet restore`.
COPY ./FleetEnterprise.Api ./FleetEnterprise.Api
WORKDIR /source/FleetEnterprise.Api
RUN dotnet restore

# This stage is for running unit and integration tests.
# It ensures that tests pass before the application is built for release.
FROM deps AS test
WORKDIR /source/FleetEnterprise.Test
# Assuming your test project is a separate folder.
COPY ./FleetEnterprise.Test .
RUN dotnet restore

FROM deps AS development
CMD ["dotnet", "watch", "run", "--verbose", "--no-launch-profile", "--hot-reload-on", "rude-edit"]

FROM deps AS build
# install missing libicu for System.Globalization.Calendars when invariant mode is set to false
RUN dotnet publish -c release -o /app --no-restore


FROM mcr.microsoft.com/dotnet/aspnet:10.0-alpine AS release
RUN apk add --no-cache icu-libs
ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=false
WORKDIR /app
COPY --from=build . .
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser
USER appuser
COPY --from=build /app ./
ENTRYPOINT [ "dotnet", "FleetEnterprise.Api.dll" ]