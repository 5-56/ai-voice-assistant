Write-Host "🎵 激活Edge TTS项目虚拟环境" -ForegroundColor Green
& .\venv\Scripts\Activate.ps1
Write-Host "✅ 虚拟环境已激活" -ForegroundColor Green
Write-Host "💡 使用以下命令运行项目:" -ForegroundColor Yellow
Write-Host "   python enhanced_tts_demo.py" -ForegroundColor Cyan
Write-Host "   python test_edge_tts_playback.py" -ForegroundColor Cyan
Write-Host "🔄 使用 deactivate 命令退出虚拟环境" -ForegroundColor Yellow
