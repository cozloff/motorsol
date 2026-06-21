package main

import (
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"

	"github.com/joho/godotenv"
)

var templates *template.Template

func homeHandler(repo UserRepository) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		users, err := repo.FindAll()
		if err != nil {
			http.Error(w, "failed to fetch users", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(users)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "Welcome")
}

func main() {
	db, err := OpenDB()
	if err != nil {
		log.Fatal("Database failed to open: ", err)
	}

	if err := db.AutoMigrate(&User{}); err != nil {
		log.Fatal("Database migration failed: ", err)
	}

	userRepo := NewGormUserRepository(db)
	if err := userRepo.Create(&User{Name: "Ada"}); err != nil {
		log.Fatal("Seed user failed: ", err)
	}

	mux := http.NewServeMux()

	godotenv.Load()

	initSessionStore()

	auth, err := NewAuthenticator()
	if err != nil {
		log.Fatalf("Failed to initialize the authenticator: %v", err)
	}

	templates = template.Must(template.ParseGlob("templates/*.html"))

	mux.HandleFunc("/", HomeHandler)
	mux.HandleFunc("/login", LoginHandler())
	mux.HandleFunc("/callback", CallbackHandler())
	mux.HandleFunc("/user", UserHandler)
	mux.HandleFunc("/logout", LogoutHandler(auth))

	err = http.ListenAndServe(":3000", mux)
	if err != nil {
		log.Fatal("Server failed to start: ", err)
	}
}
