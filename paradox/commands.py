"""
Módulo de comandos auxiliares Paradox

Funções helper para facilitar envio de comandos específicos.
"""

import logging
from . import protocol

logger = logging.getLogger(__name__)


def send_initiate_communication(connection):
    """
    Envia comando InitiateCommunication (0x72)
    
    Args:
        connection: SerialConnection - conexão serial
    
    Returns:
        bytes - dados enviados
    """
    logger.debug("Enviando InitiateCommunication")
    cmd = protocol.build_initiate_communication(user_id=0x00)
    connection.write(cmd)
    return cmd


def send_initialize_mgsp(connection, password, product_id, firmware, panel_id):
    """
    Envia comando InitializeCommunication MG/SP (0x00)
    
    Args:
        connection: SerialConnection - conexão serial
        password: bytes - senha PC (2 bytes)
        product_id: int - ID do produto
        firmware: tuple - (version, revision, minor)
        panel_id: int - ID do painel
    
    Returns:
        bytes - dados enviados
    """
    logger.debug("Enviando InitializeCommunication MG/SP")
    cmd = protocol.build_initialize_communication_mgsp(
        product_id=product_id,
        firmware_version=firmware,
        panel_id=panel_id,
        pc_password_bytes=password,
        source_id=0x01,
        user_id=0x00
    )
    connection.write(cmd)
    return cmd


def send_arm_command(connection, partition, action_code):
    """
    Envia comando de armamento
    
    Args:
        connection: SerialConnection - conexão serial
        partition: int - número da partição (0-7, 0-indexed)
        action_code: int - código da ação (ver protocol.PARTITION_ACTIONS)
    
    Returns:
        bytes - dados enviados
    """
    logger.debug(f"Enviando comando de armamento: partição={partition}, ação=0x{action_code:02X}")
    cmd = protocol.build_perform_action(
        action=action_code,
        argument=partition,
        source_id=0x01,
        user_id=0x00
    )
    connection.write(cmd)
    return cmd


def send_bypass_command(connection, zone):
    """
    Envia comando de bypass de zona
    
    Args:
        connection: SerialConnection - conexão serial
        zone: int - número da zona (0-191, 0-indexed)
    
    Returns:
        bytes - dados enviados
    """
    logger.debug(f"Enviando comando de bypass: zona={zone}")
    cmd = protocol.build_perform_action(
        action=protocol.ZONE_ACTIONS['bypass'],
        argument=zone,
        source_id=0x01,
        user_id=0x00
    )
    connection.write(cmd)
    return cmd


def send_read_eeprom(connection, address, records=1):
    """
    Envia comando de leitura de EEPROM
    
    Args:
        connection: SerialConnection - conexão serial
        address: int - endereço EEPROM
        records: int - número de registros
    
    Returns:
        bytes - dados enviados
    """
    logger.debug(f"Enviando comando de leitura EEPROM: endereço=0x{address:04X}, registros={records}")
    cmd = protocol.build_read_eeprom(
        address=address,
        records=records,
        source_id=0x01,
        user_id=0x00
    )
    connection.write(cmd)
    return cmd


def validate_checksum(data):
    """
    Valida checksum de mensagem recebida
    
    Args:
        data: bytes - mensagem completa (37 bytes)
    
    Returns:
        bool - True se checksum válido
    """
    if len(data) < 2:
        logger.warning("Mensagem muito curta para validar checksum")
        return False
    
    # Último byte é o checksum
    received_checksum = data[-1]
    calculated_checksum = protocol.calculate_checksum(data[:-1])
    
    valid = (received_checksum == calculated_checksum)
    
    if not valid:
        logger.warning(f"Checksum inválido: recebido=0x{received_checksum:02X}, "
                      f"calculado=0x{calculated_checksum:02X}")
    else:
        logger.debug(f"Checksum válido: 0x{received_checksum:02X}")
    
    return valid


def parse_perform_action_response(data):
    """
    Faz parse de resposta PerformAction
    
    Args:
        data: bytes - mensagem de resposta (0x4X)
    
    Returns:
        dict - informações da resposta ou None
    """
    if len(data) < 2:
        return None
    
    command = data[0]
    
    # 0x40 = sucesso
    # 0x41-0x4F = diferentes resultados
    result_codes = {
        0x40: "success",
        0x41: "fail",
        0x42: "invalid_argument",
        0x43: "user_code_required",
    }
    
    result = result_codes.get(command, "unknown")
    
    info = {
        'command': command,
        'result': result,
        'success': (command == 0x40)
    }
    
    logger.debug(f"PerformAction response: 0x{command:02X} ({result})")
    
    return info


def parse_read_eeprom_response(data):
    """
    Faz parse de resposta ReadEEPROM
    
    Args:
        data: bytes - mensagem de resposta (0x5X)
    
    Returns:
        dict - informações da resposta ou None
    """
    try:
        parsed = protocol.ReadEEPROMResponse.parse(data)
        
        info = {
            'command': parsed.fields.po.command,
            'address': parsed.fields.address,
            'records': parsed.fields.records,
            'data': parsed.fields.data,
        }
        
        logger.debug(f"ReadEEPROM response: endereço=0x{info['address']:04X}, "
                    f"registros={info['records']}, bytes={len(info['data'])}")
        
        return info
        
    except Exception as e:
        logger.error(f"Erro ao fazer parse de ReadEEPROM response: {e}")
        return None


def get_action_name(action_code):
    """
    Retorna nome legível de código de ação
    
    Args:
        action_code: int - código da ação
    
    Returns:
        str - nome da ação ou "unknown"
    """
    # Inverte dicionários para busca reversa
    for action_dict in [protocol.PARTITION_ACTIONS, protocol.ZONE_ACTIONS, protocol.PGM_ACTIONS]:
        for name, code in action_dict.items():
            if code == action_code:
                return name
    
    return f"unknown_0x{action_code:02X}"


def format_hex_dump(data, bytes_per_line=16):
    """
    Formata dados binários em hexdump legível
    
    Args:
        data: bytes - dados a formatar
        bytes_per_line: int - bytes por linha (default 16)
    
    Returns:
        str - representação hexdump
    """
    lines = []
    
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i+bytes_per_line]
        
        # Offset
        offset = f"{i:04X}"
        
        # Bytes em hex
        hex_part = ' '.join([f"{b:02X}" for b in chunk])
        hex_part = hex_part.ljust(bytes_per_line * 3)
        
        # ASCII (printable chars)
        ascii_part = ''.join([chr(b) if 32 <= b < 127 else '.' for b in chunk])
        
        lines.append(f"{offset}  {hex_part}  {ascii_part}")
    
    return '\n'.join(lines)
