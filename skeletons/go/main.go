// The smallest plugin that the core will talk to, in Go.
//
// Everything a plugin must do is here: say what it is, say whether it is
// well, and answer the endpoints for the capabilities it claimed. Copy it,
// change the manifest, fill in the one handler you care about.
//
//	go run .        # then: make check-plugin ENDPOINT=http://localhost:9101
//
// The protocol is in docs/PLUGIN-SDK.md in the core repository.
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
)

type manifest struct {
	ID              string   `json:"id"`
	Name            string   `json:"name"`
	Version         string   `json:"version"`
	ProtocolVersion int      `json:"protocol_version"`
	Vendor          string   `json:"vendor"`
	Description     string   `json:"description"`
	Capabilities    []string `json:"capabilities"`
}

type event struct {
	ID       string `json:"id"`
	Kind     string `json:"kind"`
	Severity string `json:"severity"`
	Title    string `json:"title"`
	Detail   string `json:"detail"`
}

type deliveryRequest struct {
	Event event `json:"event"`
}

func env(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

func main() {
	token := os.Getenv("PLUGIN_TOKEN")
	port := env("PORT", "9101")
	me := manifest{
		ID:      env("PLUGIN_ID", "skeleton-go"),
		Name:    "Go skeleton",
		Version: "0.1.0",
		// The core refuses a plugin speaking a protocol it does not know,
		// so this is not decoration.
		ProtocolVersion: 1,
		Vendor:          "example",
		Description:     "The smallest thing the core will talk to.",
		// Claim only what you implement: the core refuses a call for a
		// capability the manifest does not list, before it reaches the
		// network.
		Capabilities: []string{"event_sink"},
	}

	reply := func(w http.ResponseWriter, status int, body any) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_ = json.NewEncoder(w).Encode(body)
	}
	guard := func(next http.HandlerFunc) http.HandlerFunc {
		return func(w http.ResponseWriter, r *http.Request) {
			if token != "" && r.Header.Get("Authorization") != "Bearer "+token {
				reply(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
				return
			}
			next(w, r)
		}
	}

	http.HandleFunc("/v1/plugin/manifest", guard(func(w http.ResponseWriter, r *http.Request) {
		reply(w, http.StatusOK, me)
	}))
	http.HandleFunc("/v1/plugin/health", guard(func(w http.ResponseWriter, r *http.Request) {
		// Say no when you mean no: an unhealthy plugin reporting ok is worse
		// than one that is honestly down.
		reply(w, http.StatusOK, map[string]any{"status": "ok", "plugin_id": me.ID, "details": nil})
	}))
	http.HandleFunc("/v1/events", guard(func(w http.ResponseWriter, r *http.Request) {
		var request deliveryRequest
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			reply(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		fmt.Printf("%s: %s\n", request.Event.Severity, request.Event.Title)
		// delivered:false is a correct answer — the core records it and does
		// not retry. An error status is what gets retried.
		reply(w, http.StatusOK, map[string]any{"delivered": true, "detail": nil})
	}))

	log.Printf("%s listening on %s", me.ID, port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
