terraform {
  backend "s3" {
    bucket         = "poke-chaser-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "poke-chaser-terraform-locks"
    encrypt        = true
  }
}
