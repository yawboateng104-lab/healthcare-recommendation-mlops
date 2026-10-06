# Peering between the dedicated healthcare recommendation VPC and the
# existing Jenkins/PostgreSQL VPC.
#
# Jenkins/PostgreSQL VPC: 172.31.0.0/16
# Lab VPC:                 10.70.0.0/16

resource "aws_vpc_peering_connection" "jenkins_postgres" {
  vpc_id      = aws_vpc.main.id
  peer_vpc_id = "vpc-05a603717cbca1101"

  auto_accept = true

  tags = {
    Name = "${local.name_prefix}-jenkins-postgres-peer"
  }
}

# Allow private lab workloads such as EKS pods/nodes to reach
# PostgreSQL/Jenkins resources in the existing VPC.
resource "aws_route" "lab_to_jenkins_postgres" {
  route_table_id            = aws_route_table.private.id
  destination_cidr_block    = "172.31.0.0/16"
  vpc_peering_connection_id = aws_vpc_peering_connection.jenkins_postgres.id
}

# Return route from the Jenkins/PostgreSQL VPC to the dedicated lab VPC.
#
# This is the existing default VPC main route table. Terraform manages
# only this individual route, not the route table itself.
resource "aws_route" "jenkins_postgres_to_lab" {
  route_table_id            = "rtb-03cdce78be34ea1c6"
  destination_cidr_block    = var.vpc_cidr
  vpc_peering_connection_id = aws_vpc_peering_connection.jenkins_postgres.id
}
