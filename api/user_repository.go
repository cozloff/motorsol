package main

import "gorm.io/gorm"

type User struct {
	ID   uint `gorm:"primaryKey"`
	Name string
}

type UserRepository interface {
	Create(user *User) error
	FindAll() ([]User, error)
}

type GormUserRepository struct {
	db *gorm.DB
}

func NewGormUserRepository(db *gorm.DB) *GormUserRepository {
	return &GormUserRepository{db: db}
}

func (r *GormUserRepository) Create(user *User) error {
	return r.db.Create(user).Error
}

func (r *GormUserRepository) FindAll() ([]User, error) {
	var users []User
	err := r.db.Find(&users).Error
	return users, err
}
