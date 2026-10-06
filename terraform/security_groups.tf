# Allow Healthcare EKS workloads in the dedicated VPC to reach
# the Healthcare Redis online feature store on the existing EC2 host.
#
# This manages only the ingress rule and does not take ownership
# of the existing EC2 security group.

resource "aws_vpc_security_group_ingress_rule" "eks_to_redis" {
  security_group_id = "sg-0392a97a195795076"

  description = "Healthcare EKS VPC to Redis"

  cidr_ipv4   = var.vpc_cidr
  from_port   = 6379
  to_port     = 6379
  ip_protocol = "tcp"

  tags = {
    Name = "${local.name_prefix}-redis-ingress"
  }
}
