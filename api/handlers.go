package main

import (
	"encoding/gob"
	"net/http"
	"os"

	"github.com/gorilla/sessions"
	"github.com/markbates/goth/gothic"
)

var store *sessions.CookieStore

func init() {
	gob.Register(map[string]interface{}{})
}

func initSessionStore() {
	store = sessions.NewCookieStore([]byte(os.Getenv("SESSION_SECRET")))
	store.Options = &sessions.Options{
		Path:     "/",
		MaxAge:   86400,
		HttpOnly: true,
		Secure:   false, // Set to true in production (requires HTTPS)
		SameSite: http.SameSiteLaxMode,
	}
	gothic.Store = store
}

// HomeHandler renders the home page or redirects to /user if already logged in.
func HomeHandler(w http.ResponseWriter, r *http.Request) {
	session, _ := store.Get(r, "auth-session")
	if session.Values["profile"] != nil {
		http.Redirect(w, r, "/user", http.StatusSeeOther)
		return
	}
	if err := templates.ExecuteTemplate(w, "home.html", nil); err != nil {
		http.Error(w, "Internal error", http.StatusInternalServerError)
	}
}

// LoginHandler starts the Goth login flow.
func LoginHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		gothic.BeginAuthHandler(w, withProvider(r))
	}
}

// CallbackHandler completes the Goth login flow and stores the user profile.
func CallbackHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := gothic.CompleteUserAuth(w, withProvider(r))
		if err != nil {
			http.Error(w, "Failed to complete authentication", http.StatusUnauthorized)
			return
		}

		session, _ := store.Get(r, "auth-session")
		session.Values["access_token"] = user.AccessToken
		session.Values["profile"] = map[string]interface{}{
			"nickname": user.NickName,
			"name":     user.Name,
			"picture":  user.AvatarURL,
			"email":    user.Email,
		}
		if err := session.Save(r, w); err != nil {
			http.Error(w, "Internal error", http.StatusInternalServerError)
			return
		}

		http.Redirect(w, r, "/user", http.StatusTemporaryRedirect)
	}
}

// UserHandler displays the authenticated user's profile.
func UserHandler(w http.ResponseWriter, r *http.Request) {
	session, _ := store.Get(r, "auth-session")
	profile, ok := session.Values["profile"].(map[string]interface{})
	if !ok {
		http.Redirect(w, r, "/", http.StatusSeeOther)
		return
	}

	if err := templates.ExecuteTemplate(w, "user.html", profile); err != nil {
		http.Error(w, "Internal error", http.StatusInternalServerError)
	}
}

// LogoutHandler clears the session and redirects to the identity provider logout endpoint.
func LogoutHandler(auth *Authenticator) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		session, _ := store.Get(r, "auth-session")
		session.Options.MaxAge = -1
		session.Save(r, w)
		_ = gothic.Logout(w, withProvider(r))

		scheme := "http"
		if r.TLS != nil {
			scheme = "https"
		}
		returnTo := scheme + "://" + r.Host

		http.Redirect(w, r, auth.LogoutRedirectURL(returnTo), http.StatusTemporaryRedirect)
	}
}

func withProvider(r *http.Request) *http.Request {
	return gothic.GetContextWithProvider(r, authProvider)
}
