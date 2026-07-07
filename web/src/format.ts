export const sgd = (n: number) =>
  n.toLocaleString("en-SG", {
    style: "currency",
    currency: "SGD",
    maximumFractionDigits: 0,
  });

export const signedSgd = (n: number) => (n >= 0 ? `+${sgd(n)}` : `−${sgd(Math.abs(n))}`);
