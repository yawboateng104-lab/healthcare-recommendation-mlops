resource "aws_eks_cluster" "main" {
  name     = "${local.name_prefix}-eks"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.36"

  vpc_config {
    subnet_ids = concat(
      aws_subnet.private[*].id,
      aws_subnet.public[*].id
    )

    endpoint_private_access = true
    endpoint_public_access  = true

    public_access_cidrs = [
      "3.21.237.108/32"
    ]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy
  ]

  tags = local.common_tags
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name_prefix}-nodes"
  node_role_arn   = aws_iam_role.eks_nodes.arn

  subnet_ids = aws_subnet.private[*].id

  instance_types = ["t3.medium"]

  scaling_config {
    desired_size = 2
    min_size     = 2
    max_size     = 3
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_ecr_read_only,
    aws_iam_role_policy_attachment.eks_cni_policy
  ]

  tags = local.common_tags
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name  = aws_eks_cluster.main.name
  addon_name    = "vpc-cni"
  addon_version = "v1.23.0-eksbuild.1"

  tags = local.common_tags
}

resource "aws_eks_addon" "coredns" {
  cluster_name  = aws_eks_cluster.main.name
  addon_name    = "coredns"
  addon_version = "v1.14.3-eksbuild.16"

  depends_on = [
    aws_eks_node_group.main
  ]

  tags = local.common_tags
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name  = aws_eks_cluster.main.name
  addon_name    = "kube-proxy"
  addon_version = "v1.36.0-eksbuild.17"

  tags = local.common_tags
}
