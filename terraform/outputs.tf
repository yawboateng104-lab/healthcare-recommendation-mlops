output "vpc_id" {
  description = "Dedicated healthcare recommendation MLOps VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_id" {
  description = "NAT Gateway used by private lab subnets"
  value       = aws_nat_gateway.main.id
}

output "nat_public_ip" {
  description = "Elastic IP attached to the NAT Gateway"
  value       = aws_eip.nat.public_ip
}

output "ecr_repository_url" {
  description = "ECR repository URL for the healthcare recommendation inference service"
  value       = aws_ecr_repository.inference.repository_url
}

output "jenkins_postgres_vpc_peering_id" {
  description = "VPC peering connection between the Healthcare EKS VPC and Jenkins/Redis VPC"
  value       = aws_vpc_peering_connection.jenkins_postgres.id
}
