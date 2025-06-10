"""
系统监控API端点
"""
import logging
import psutil
import os
import time
import platform
import subprocess
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.admin.auth import get_admin_user, AdminBase
from app.admin.schemas.admin import SystemMetricsResponse

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

def get_mac_gpu_info():
    """获取Mac系统的GPU信息"""
    try:
        # 检查是否为Mac系统
        if platform.system() != "Darwin":
            return None
        
        # 使用ioreg命令获取GPU信息
        cmd = "ioreg -l | grep IOGPUUtilization"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0 or not result.stdout:
            # 尝试使用powermetrics命令获取GPU信息
            cmd = "sudo powermetrics --samplers gpu_power -n 1 -i 100"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0 or not result.stdout:
                return None
            
            # 解析powermetrics输出
            lines = result.stdout.split('\n')
            gpu_info = {}
            
            for line in lines:
                if "GPU active frequency" in line:
                    parts = line.strip().split(':')
                    if len(parts) >= 2:
                        freq_parts = parts[1].strip().split()
                        if len(freq_parts) >= 1:
                            try:
                                current = float(freq_parts[0])
                                # 假设最大频率为1000MHz（可能需要调整）
                                gpu_info["percent"] = current / 10.0
                            except (ValueError, IndexError):
                                pass
            
            # 如果没有找到GPU利用率信息
            if "percent" not in gpu_info:
                # 使用top命令获取WindowServer进程的CPU使用率作为GPU使用的近似值
                cmd = "top -l 1 -pid $(pgrep WindowServer) | grep CPU"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout:
                    try:
                        cpu_usage = float(result.stdout.split()[2].replace('%', ''))
                        # WindowServer的CPU使用率通常与GPU使用率相关
                        gpu_info["percent"] = min(100.0, cpu_usage * 1.5)
                    except (ValueError, IndexError):
                        gpu_info["percent"] = 0.0
                else:
                    gpu_info["percent"] = 0.0
            
            # 获取GPU内存信息（Mac OS不直接提供此信息，这里使用估计值）
            vm = psutil.virtual_memory()
            gpu_info["name"] = "Apple Silicon GPU"
            gpu_info["memory_total"] = vm.total // 4  # 假设GPU内存为系统内存的1/4
            gpu_info["memory_used"] = int(gpu_info["memory_total"] * (gpu_info["percent"] / 100.0))
            gpu_info["memory_free"] = gpu_info["memory_total"] - gpu_info["memory_used"]
            gpu_info["memory_percent"] = gpu_info["percent"]
            
            return gpu_info
        else:
            # 解析ioreg输出
            output = result.stdout
            if "IOGPUUtilization" in output:
                try:
                    # 尝试提取GPU利用率
                    utilization_part = output.split("IOGPUUtilization")[1].split("=")[1].split(",")[0]
                    gpu_percent = float(utilization_part.strip())
                    
                    gpu_info = {
                        "name": "Apple Silicon GPU",
                        "percent": gpu_percent,
                    }
                    
                    # 获取GPU内存信息（Mac OS不直接提供此信息，这里使用估计值）
                    vm = psutil.virtual_memory()
                    gpu_info["memory_total"] = vm.total // 4  # 假设GPU内存为系统内存的1/4
                    gpu_info["memory_used"] = int(gpu_info["memory_total"] * (gpu_percent / 100.0))
                    gpu_info["memory_free"] = gpu_info["memory_total"] - gpu_info["memory_used"]
                    gpu_info["memory_percent"] = gpu_percent
                    
                    return gpu_info
                except Exception as e:
                    logger.error(f"解析GPU信息失败: {str(e)}")
            
            return None
    except Exception as e:
        logger.error(f"获取GPU信息失败: {str(e)}")
        return None

@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(admin_user: AdminBase = Depends(get_admin_user)):
    """获取系统监控指标"""
    try:
        # CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # 内存信息
        memory = psutil.virtual_memory()
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        
        # GPU信息
        gpu_info = get_mac_gpu_info()
        
        response = {
            "cpu": {
                "percent": cpu_percent,
                "cores": cpu_count
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "timestamp": datetime.now()
        }
        
        # 如果有GPU信息，添加到响应中
        if gpu_info:
            response["gpu"] = gpu_info
        
        return response
    except Exception as e:
        logger.error(f"获取系统指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统指标失败: {str(e)}")

@router.get("/info")
async def get_system_info(admin_user: AdminBase = Depends(get_admin_user)):
    """获取系统信息"""
    try:
        # 系统信息
        system_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "uptime": int(time.time() - psutil.boot_time())
        }
        
        # 进程信息
        current_process = psutil.Process(os.getpid())
        process_info = {
            "pid": current_process.pid,
            "name": current_process.name(),
            "username": current_process.username(),
            "create_time": datetime.fromtimestamp(current_process.create_time()).isoformat(),
            "cpu_percent": current_process.cpu_percent(interval=1),
            "memory_percent": current_process.memory_percent(),
            "status": current_process.status(),
            "threads": len(current_process.threads())
        }
        
        # 网络信息
        net_io = psutil.net_io_counters()
        network_info = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "connections": len(psutil.net_connections())
        }
        
        return {
            "system": system_info,
            "process": process_info,
            "network": network_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")

@router.get("/processes")
async def get_processes(
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("cpu_percent", description="排序字段，可选：cpu_percent, memory_percent, create_time"),
    admin_user: AdminBase = Depends(get_admin_user)
):
    """获取进程列表"""
    try:
        # 获取进程列表
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'create_time', 'status']):
            try:
                # 获取进程信息
                proc_info = proc.info
                proc_info['cpu_percent'] = proc.cpu_percent(interval=0.1)
                proc_info['memory_percent'] = proc.memory_percent()
                
                # 格式化创建时间
                if 'create_time' in proc_info and proc_info['create_time']:
                    proc_info['create_time'] = datetime.fromtimestamp(proc_info['create_time']).isoformat()
                    
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # 排序
        valid_sort_fields = ["cpu_percent", "memory_percent", "create_time"]
        sort_field = sort_by if sort_by in valid_sort_fields else "cpu_percent"
        
        # 对于create_time，我们按降序排序（最新的在前）
        if sort_field == "create_time":
            processes = sorted(
                [p for p in processes if p.get(sort_field)], 
                key=lambda x: x.get(sort_field, ""),
                reverse=True
            )
        else:
            # 对于CPU和内存使用率，按降序排序（使用率高的在前）
            processes = sorted(
                [p for p in processes if p.get(sort_field) is not None], 
                key=lambda x: x.get(sort_field, 0),
                reverse=True
            )
            
        # 限制返回数量
        processes = processes[:limit]
        
        return {
            "processes": processes,
            "total": len(processes),
            "sort_by": sort_field,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取进程列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取进程列表失败: {str(e)}")

@router.get("/logs")
async def get_system_logs(
    lines: int = Query(100, ge=1, le=1000),
    log_file: Optional[str] = Query(None, description="日志文件名，默认为应用日志"),
    admin_user: AdminBase = Depends(get_admin_user)
):
    """获取系统日志"""
    try:
        # 默认日志文件
        default_log_file = "logs/app.log"
        target_log = log_file or default_log_file
        
        # 安全检查：确保日志文件在日志目录中
        if not target_log.startswith("logs/"):
            raise HTTPException(status_code=403, detail="只允许访问logs目录中的日志文件")
        
        # 检查文件是否存在
        if not os.path.exists(target_log):
            raise HTTPException(status_code=404, detail=f"日志文件 {target_log} 不存在")
            
        # 读取日志内容
        logs = []
        try:
            with open(target_log, "r") as f:
                all_lines = f.readlines()
                # 取最后的n行
                logs = all_lines[-lines:] if lines < len(all_lines) else all_lines
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取日志文件失败: {str(e)}")
            
        return {
            "file": target_log,
            "lines": len(logs),
            "content": logs,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统日志失败: {str(e)}") 