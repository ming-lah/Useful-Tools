import numpy as np
import cv2

def linear(img: np.ndarray, alpha: float=1.0, beta: float=0.0) -> np.ndarray:
    """
    linear transform
    """
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

def gamma(img: np.ndarray, gamma: float=1.0) -> np.ndarray:
    if gamma <= 0:
        raise ValueError("gamma must be > 0")
    
    inv = 1.0 / gamma
    table = ((np.arange(0, 256) / 255.0) ** inv * 255.0).clip(0, 255).astype(np.uint8)
    return cv2.LUT(img, table)

def clahe(img: np.ndarray, clip_limit: float=2.0, tile: int = 8) -> np.ndarray:
    """
    对LAB的L通道进行直方图均衡化而
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    # clip_limit：限制对比度放大的阈值
    # tile：切块的大小
    c = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile, tile))
    l2 = c.apply(l)
    lab2 = cv2.merge((l2, a, b))
    return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)

def median(img: np.ndarray, k: int=3) -> np.ndarray:
    if k < 3 or k % 2 == 0:
        raise ValueError("k must be an odd integer >= 3")
    return cv2.medianBlur(img, k)

def unsharp(img: np.ndarray, sigma: float=1.2, amount: float=1.0) -> np.ndarray:
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    blur = cv2.GaussianBlur(img, (0, 0), sigmaX=float(sigma))
    return cv2.addWeighted(img, 1.0 + float(amount), blur, -float(amount), 0)

def sobel(img: np.ndarray, ksize: int=3, normalize: bool=True) -> np.ndarray:
    ksize = int(ksize)
    if ksize < 1 or ksize % 2 == 0:
        raise ValueError("ksize must be an odd integer >= 1")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=ksize)
    mag = cv2.magnitude(gx, gy)
    if normalize:
        mmax = float(mag.max()) if mag.size else 0.0
        if mmax > 1e-6:
            mag = mag * (255.0 / mmax)
    mag = np.clip(mag, 0, 255).astype(np.uint8)
    return mag
