# train.py
import os
import argparse
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import Dataset, DataLoader, DistributedSampler

import perun

def ddp_setup() -> int:
    """
    Initialize torch.distributed under torchrun or Slurm and select the correct local GPU.

    Returns
    -------
    int
        local_rank used for device placement.
    """

    local_rank = int(os.environ.get("LOCAL_RANK"))
    torch.cuda.set_device(local_rank)
    dist.init_process_group(backend="nccl")

    uuid = str(torch.cuda.get_device_properties(local_rank).uuid)
    if dist.get_rank() == 0:
        print(f"DDP init: world_size={dist.get_world_size()} master={os.environ['MASTER_ADDR']}:{os.environ['MASTER_PORT']}")
    print(f"Initialized DDP with rank {dist.get_rank()} local_rank {local_rank} device {uuid}")
    return local_rank


class ToyDataset(Dataset):
    """
    Simple synthetic regression dataset.

    Each sample:
        x: FloatTensor[batch=1, feat=32]
        y: FloatTensor[batch=1, out=1]
    """
    def __init__(self, n: int = 4096, in_dim: int = 32):
        g = torch.Generator().manual_seed(0)
        self.x = torch.randn(n, in_dim, generator=g)  # [N, 32]
        w = torch.randn(in_dim, 1, generator=g)       # [32, 1]
        self.y = self.x @ w + 0.1 * torch.randn(n, 1, generator=g)  # [N, 1]

    def __len__(self) -> int:
        return self.x.size(0)

    def __getitem__(self, i: int):
        return self.x[i], self.y[i]


class TinyMLP(torch.nn.Module):
    """
    Two-layer MLP.

    Forward
    -------
    x: FloatTensor[batch, 32]
    returns: FloatTensor[batch, 1]
    """
    def __init__(self, in_dim: int = 32, hid: int = 128):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(in_dim, hid),
            torch.nn.ReLU(),
            torch.nn.Linear(hid, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def average_tensor(t: torch.Tensor) -> torch.Tensor:
    """
    All-reduce average a scalar tensor across ranks.
    """
    dist.all_reduce(t, op=dist.ReduceOp.SUM)
    t /= dist.get_world_size()
    return t


def train_one_epoch(model: DDP, loader: DataLoader, opt: torch.optim.Optimizer, device: torch.device, epoch: int):
    """
    Run one training epoch.

    Parameters
    ----------
    model : DDP-wrapped TinyMLP
    loader : DataLoader over ToyDataset
    opt : torch.optim.Optimizer
    device : torch.device
    epoch : int
    """
    model.train()
    loss_fn = torch.nn.MSELoss()
    sampler = loader.sampler if isinstance(loader.sampler, DistributedSampler) else None
    if sampler is not None:
        sampler.set_epoch(epoch)

    running = torch.zeros(1, device=device)  # [1]
    for x, y in loader:  # x:[B,32], y:[B,1]
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        pred = model(x)                  # [B,1]
        loss = loss_fn(pred, y)          # []
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        running += loss.detach()

    running /= max(1, len(loader))
    avg = average_tensor(running)  # rank-avg
    return avg.item()

def train(args, model, loader, opt, device):
    for epoch in range(args.epochs):
        avg_loss = train_one_epoch(model, loader, opt, device, epoch)
        if dist.get_rank() == 0:
            print(f"epoch {epoch} loss {avg_loss:.6f}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=3)
    args = parser.parse_args()

    local_rank = ddp_setup()
    device = torch.device("cuda", local_rank)

    dataset = ToyDataset(n=8192, in_dim=32)
    sampler = DistributedSampler(dataset, shuffle=True, drop_last=False)
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        sampler=sampler,
        num_workers=2,
        pin_memory=True,
        persistent_workers=False,
    )

    model = TinyMLP(in_dim=32, hid=128).to(device)
    model = DDP(model, find_unused_parameters=False, device_ids=[local_rank])
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)

    if dist.get_rank() % 4 == 0:
        train_func = perun.perun(app_name=f"train_{dist.get_rank()}")(train)
    else:
        train_func = train

    train_func(args, model, loader, opt, device)

    dist.destroy_process_group()


if __name__ == "__main__":
    main()
