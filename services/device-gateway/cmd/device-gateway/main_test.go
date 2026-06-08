package main

import "testing"

func TestPlaceholderMessage(t *testing.T) {
	if got := placeholderMessage(); got != "device-gateway scaffold only" {
		t.Fatalf("unexpected placeholder message: %q", got)
	}
}
