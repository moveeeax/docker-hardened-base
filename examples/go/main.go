// Command example is a tiny static HTTP service used to prove that the
// hardened-go base image runs an ordinary Go binary as a non-root user with
// no shell and no libc in the final layer.
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	http.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprintln(w, "ok")
	})
	http.HandleFunc("/whoami", func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprintf(w, "uid=%d gid=%d\n", os.Getuid(), os.Getgid())
	})

	addr := ":8080"
	if v := os.Getenv("ADDR"); v != "" {
		addr = v
	}
	log.Printf("listening on %s as uid=%d", addr, os.Getuid())
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatal(err)
	}
}
