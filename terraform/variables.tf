variable "aws_region" {
  description = "AWS region for the healthcare recommendation MLOps platform"
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "healthcare-recommendation-mlops"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "lab"
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated lab VPC"
  type        = string
  default     = "10.70.0.0/16"
}

variable "availability_zones" {
  description = "Availability Zones used by the lab"
  type        = list(string)

  default = [
    "us-east-2a",
    "us-east-2b"
  ]
}

variable "public_subnet_cidrs" {
  description = "CIDRs for public subnets"
  type        = list(string)

  default = [
    "10.70.1.0/24",
    "10.70.2.0/24"
  ]
}

variable "private_subnet_cidrs" {
  description = "CIDRs for private subnets"
  type        = list(string)

  default = [
    "10.70.11.0/24",
    "10.70.12.0/24"
  ]
}
