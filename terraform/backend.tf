terraform {
  backend "s3" {
    bucket       = "provider-fraud-mlops-lab-tfstate-093113290899"
    key          = "healthcare-recommendation-mlops/lab/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}
