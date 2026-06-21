package main

import (
	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
)

func OpenDB() (*gorm.DB, error) {
	return gorm.Open(
		sqlite.Open("file::memory:?cache=shared"),
		&gorm.Config{})
}
