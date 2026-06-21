package main

import (
	"fmt"
	"net/url"
	"os"

	"github.com/markbates/goth"
	"github.com/markbates/goth/providers/openidConnect"
)

const authProvider = "openid-connect"

// Authenticator stores the Keycloak values needed outside the Goth login flow.
type Authenticator struct {
	ClientID  string
	LogoutURL string
}

// NewAuthenticator configures Goth's OpenID Connect provider for Keycloak.
func NewAuthenticator() (*Authenticator, error) {
	clientID := os.Getenv("KEYCLOAK_CLIENT_ID")
	clientSecret := os.Getenv("KEYCLOAK_CLIENT_SECRET")
	callbackURL := os.Getenv("KEYCLOAK_CALLBACK_URL")
	discoveryURL := os.Getenv("KEYCLOAK_DISCOVERY_URL")
	logoutURL := os.Getenv("KEYCLOAK_LOGOUT_URL")

	if clientID == "" || clientSecret == "" || callbackURL == "" || discoveryURL == "" {
		return nil, fmt.Errorf("missing Keycloak environment variables")
	}

	provider, err := openidConnect.New(clientID, clientSecret, callbackURL, discoveryURL, "openid", "profile", "email")
	if err != nil {
		return nil, fmt.Errorf("failed to configure Keycloak provider: %w", err)
	}

	goth.UseProviders(
		provider,
	)

	return &Authenticator{
		ClientID:  clientID,
		LogoutURL: logoutURL,
	}, nil
}

func (a *Authenticator) LogoutRedirectURL(returnTo string) string {
	if a.LogoutURL == "" {
		return returnTo
	}

	logoutURL, err := url.Parse(a.LogoutURL)
	if err != nil {
		return returnTo
	}

	params := logoutURL.Query()
	params.Set("client_id", a.ClientID)
	params.Set("post_logout_redirect_uri", returnTo)
	logoutURL.RawQuery = params.Encode()

	return logoutURL.String()
}
