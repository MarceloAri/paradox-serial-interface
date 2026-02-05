"""
Módulo de comunicação serial com centrais Paradox

Implementa a camada de comunicação serial com logging detalhado.
"""

import serial
import logging
import time

logger = logging.getLogger(__name__)


class SerialConnection:
    """
    Classe para gerenciar comunicação serial com centrais Paradox
    
    Attributes:
        port: str - porta serial (ex: /dev/ttyUSB0, COM3)
        baudrate: int - velocidade de comunicação (default 9600)
        timeout: float - timeout de leitura em segundos
    """
    
    def __init__(self, port, baudrate=9600, timeout=5):
        """
        Inicializa conexão serial
        
        Args:
            port: str - porta serial
            baudrate: int - velocidade (default 9600)
            timeout: float - timeout em segundos (default 5)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self._connected = False
        
    def connect(self):
        """
        Abre porta serial
        
        Returns:
            bool - True se conectado com sucesso
        
        Raises:
            serial.SerialException - se falhar ao abrir porta
        """
        try:
            logger.info(f"Conectando à porta {self.port} @ {self.baudrate} baud")
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self._connected = True
            logger.info("Conexão serial estabelecida com sucesso")
            return True
        except serial.SerialException as e:
            logger.error(f"Erro ao abrir porta serial: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao conectar: {e}")
            raise
    
    def disconnect(self):
        """Fecha porta serial"""
        if self.serial and self.serial.is_open:
            logger.info("Fechando conexão serial")
            self.serial.close()
            self._connected = False
    
    def is_connected(self):
        """Verifica se conexão está ativa"""
        return self._connected and self.serial and self.serial.is_open
    
    def write(self, data):
        """
        Envia dados pela porta serial com logging
        
        Args:
            data: bytes - dados a enviar
        
        Returns:
            int - número de bytes enviados
        
        Raises:
            serial.SerialException - se erro ao enviar
        """
        if not self.is_connected():
            raise serial.SerialException("Porta serial não está conectada")
        
        try:
            # Log em hexadecimal
            hex_data = ' '.join([f'{b:02X}' for b in data])
            logger.debug(f"TX ({len(data)} bytes): {hex_data}")
            
            bytes_written = self.serial.write(data)
            self.serial.flush()  # Garante que dados são enviados
            
            return bytes_written
        except serial.SerialTimeoutException:
            logger.error("Timeout ao enviar dados")
            raise
        except Exception as e:
            logger.error(f"Erro ao enviar dados: {e}")
            raise
    
    def read(self, length):
        """
        Lê número específico de bytes com logging
        
        Args:
            length: int - número de bytes a ler
        
        Returns:
            bytes - dados lidos (pode ser menor que length se timeout)
        
        Raises:
            serial.SerialException - se erro ao ler
        """
        if not self.is_connected():
            raise serial.SerialException("Porta serial não está conectada")
        
        try:
            data = self.serial.read(length)
            
            if len(data) > 0:
                # Log em hexadecimal
                hex_data = ' '.join([f'{b:02X}' for b in data])
                logger.debug(f"RX ({len(data)} bytes): {hex_data}")
            else:
                logger.debug(f"RX: Nenhum dado recebido (timeout)")
            
            return data
        except Exception as e:
            logger.error(f"Erro ao ler dados: {e}")
            raise
    
    def read_variable_length(self, max_length=37, initial_timeout=None):
        """
        Lê mensagem de tamanho variável
        
        Para mensagens Paradox:
        - Mensagens padrão têm 37 bytes
        - Primeiro byte pode indicar tamanho se > 4
        
        Args:
            max_length: int - tamanho máximo a ler (default 37)
            initial_timeout: float - timeout para primeiro byte (usa self.timeout se None)
        
        Returns:
            bytes - mensagem completa lida
        """
        if not self.is_connected():
            raise serial.SerialException("Porta serial não está conectada")
        
        # Salva timeout original
        original_timeout = self.serial.timeout
        if initial_timeout is not None:
            self.serial.timeout = initial_timeout
        
        try:
            # Lê primeiro byte para determinar tamanho
            first_byte = self.serial.read(1)
            if len(first_byte) == 0:
                self.serial.timeout = original_timeout
                return b''
            
            # Restaura timeout original para resto da mensagem
            self.serial.timeout = original_timeout
            
            # Determina tamanho da mensagem
            if first_byte[0] > 4:
                # Tamanho pode estar no primeiro byte
                message_length = first_byte[0]
                if message_length > max_length:
                    message_length = max_length
            else:
                # Mensagem padrão de 37 bytes
                message_length = 37
            
            # Lê restante da mensagem
            remaining = message_length - 1
            rest = self.serial.read(remaining)
            
            data = first_byte + rest
            
            if len(data) > 0:
                hex_data = ' '.join([f'{b:02X}' for b in data])
                logger.debug(f"RX ({len(data)} bytes): {hex_data}")
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao ler mensagem de tamanho variável: {e}")
            self.serial.timeout = original_timeout
            raise
    
    def available(self):
        """
        Retorna número de bytes disponíveis no buffer
        
        Returns:
            int - bytes disponíveis
        """
        if not self.is_connected():
            return 0
        return self.serial.in_waiting
    
    def flush_input(self):
        """Limpa buffer de entrada"""
        if self.is_connected():
            self.serial.reset_input_buffer()
            logger.debug("Buffer de entrada limpo")
    
    def flush_output(self):
        """Limpa buffer de saída"""
        if self.is_connected():
            self.serial.reset_output_buffer()
            logger.debug("Buffer de saída limpo")
    
    def __enter__(self):
        """Context manager: abre conexão"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: fecha conexão"""
        self.disconnect()
        return False
