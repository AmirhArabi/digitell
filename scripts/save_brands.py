import os

logos = {
    'apple.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 170" width="100%" height="100%"><path fill="#1A1A1E" d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.7-3.04-7.66-7.74-11.88-14.11-6.19-9.35-11.12-19.78-14.79-31.28-3.67-11.5-5.51-22.38-5.51-32.63 0-14.02 3.6-25.75 10.8-35.19 7.2-9.44 16.35-14.28 27.46-14.52 4.9.11 10.42 1.39 16.56 3.84 6.14 2.45 10.14 3.73 12 3.84 2.29-.11 6.53-1.46 12.73-4.06 6.2-2.6 11.75-3.83 16.65-3.7 12.53.64 22.39 4.96 29.58 12.96-10.99 6.64-16.37 15.71-16.14 27.2.22 9.04 3.72 16.8 10.5 23.28 6.78 6.48 14.86 10.18 24.24 11.1-2.18 6.42-4.94 13.1-8.29 20.03zM119.22 31.02c0-7.08 2.61-13.88 7.84-20.4 5.22-6.52 11.83-10.62 19.82-12.3 1.09 7.08-1.14 13.93-6.69 20.55-5.55 6.62-12.55 10.67-20.97 12.15z"/></svg>',
    'samsung.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" width="100%" height="100%"><text x="50%" y="68%" text-anchor="middle" font-family="Arial Black, sans-serif" font-weight="900" font-size="30" letter-spacing="2" fill="#1428A0">SAMSUNG</text></svg>',
    'xiaomi.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%"><rect width="100" height="100" rx="26" fill="#FF6900"/><path fill="#FFFFFF" d="M33 26h10v34c0 3 2 5 5 5s5-2 5-5V26h10v34c0 8.8-7.2 16-16 16s-16-7.2-16-16V26zm23 20h10v20H56V46z"/></svg>',
    'sony.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" width="100%" height="100%"><text x="50%" y="68%" text-anchor="middle" font-family="Times New Roman, serif" font-weight="900" font-size="38" letter-spacing="6" fill="#111827">SONY</text></svg>',
    'asus.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" width="100%" height="100%"><text x="50%" y="68%" text-anchor="middle" font-family="Impact, Arial Black, sans-serif" font-weight="900" font-size="42" letter-spacing="4" fill="#00539B">ASUS</text></svg>',
    'anker.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" width="100%" height="100%"><text x="50%" y="68%" text-anchor="middle" font-family="Arial Black, sans-serif" font-weight="900" font-size="34" letter-spacing="2" fill="#00A2E8">ANKER</text></svg>',
    'jbl.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 70" width="100%" height="100%"><rect width="120" height="70" rx="16" fill="#FF4E00"/><text x="50%" y="68%" text-anchor="middle" font-family="Impact, Arial Black, sans-serif" font-weight="900" font-size="42" fill="#FFFFFF">JBL</text></svg>',
    'porodo.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" width="100%" height="100%"><rect width="200" height="60" rx="14" fill="#111827"/><text x="50%" y="66%" text-anchor="middle" font-family="Arial Black, sans-serif" font-weight="900" font-size="28" letter-spacing="3" fill="#00E5FF">PORODO</text></svg>',
    'green-lion.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" width="100%" height="100%"><rect width="200" height="60" rx="14" fill="#052E16"/><text x="50%" y="66%" text-anchor="middle" font-family="Arial Black, sans-serif" font-weight="900" font-size="24" letter-spacing="2" fill="#22C55E">GREEN LION</text></svg>',
    'glx.svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 70" width="100%" height="100%"><rect width="120" height="70" rx="16" fill="#0284C7"/><text x="50%" y="68%" text-anchor="middle" font-family="Impact, sans-serif" font-weight="900" font-size="38" letter-spacing="2" fill="#FFFFFF">GLX</text></svg>'
}

target_dir = os.path.join('static', 'img', 'brands')
os.makedirs(target_dir, exist_ok=True)
for fname, content in logos.items():
    with open(os.path.join(target_dir, fname), 'w', encoding='utf-8') as f:
        f.write(content.strip())
print(f'Successfully saved {len(logos)} brand logos to {target_dir}')
