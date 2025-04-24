import { format } from 'date-fns';

// Determine environment
const isServer = typeof window === 'undefined';

// Only import and use fs on the server side
let fs: any;
let path: any;
let logsDir: string = '';

if (isServer) {
  // Dynamic imports for server-side only
  fs = require('fs');
  path = require('path');
  
  // Ensure logs directory exists (server-side only)
  logsDir = path.join(process.cwd(), 'logs');
  if (fs.existsSync(logsDir)) {
    console.log('Logs directory exists:', logsDir);
  } else {
    try {
      fs.mkdirSync(logsDir, { recursive: true });
      console.log('Created logs directory:', logsDir);
    } catch (err) {
      console.error('Error creating logs directory:', err);
    }
  }
}

interface LogOptions {
  sessionId?: string;
  component?: string;
  toConsole?: boolean;
  toFile?: boolean;
}

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

class Logger {
  private sessionId: string;
  private component: string;
  private logFile: string | null = null;
  private toConsole: boolean;
  private toFile: boolean;

  constructor(options: LogOptions = {}) {
    this.sessionId = options.sessionId || 'app';
    this.component = options.component || 'general';
    this.toConsole = options.toConsole !== false;
    // Only enable file logging on the server
    this.toFile = isServer && options.toFile !== false;
    
    // Only set up file logging on the server
    if (isServer && this.toFile) {
      try {
        const timestamp = format(new Date(), 'yyyy-MM-dd-HH-mm-ss');
        this.logFile = path.join(logsDir, `${this.sessionId}-${timestamp}.log`);
        
        // Create session log header
        const header = `===== Session ${this.sessionId} started at ${new Date().toISOString()} =====\n`;
        fs.writeFileSync(this.logFile, header, { flag: 'a' });
      } catch (err) {
        console.error(`Failed to initialize log file:`, err);
        this.toFile = false; // Disable file logging on error
      }
    }
  }

  private formatMessage(level: LogLevel, message: string, data?: any): string {
    const timestamp = new Date().toISOString();
    let logMessage = `[${timestamp}] [${level.toUpperCase()}] [${this.component}] [${this.sessionId}] ${message}`;
    
    if (data) {
      if (typeof data === 'object') {
        try {
          const dataStr = JSON.stringify(data, null, 2);
          logMessage += `\nData: ${dataStr}`;
        } catch (err) {
          logMessage += `\nData: [Cannot stringify data: ${err}]`;
        }
      } else {
        logMessage += `\nData: ${data}`;
      }
    }
    
    return logMessage;
  }

  private writeToFile(message: string): void {
    // Skip file writing if not on server or if file logging is disabled
    if (!isServer || !this.toFile || !this.logFile) return;
    
    try {
      fs.appendFileSync(this.logFile, message + '\n');
    } catch (err) {
      console.error(`Failed to write to log file: ${err}`, err);
      this.toFile = false; // Disable future file writes to avoid repeated errors
    }
  }

  private log(level: LogLevel, message: string, data?: any): void {
    const formattedMessage = this.formatMessage(level, message, data);
    
    if (this.toConsole) {
      // Use console methods based on level
      switch (level) {
        case 'debug':
          console.debug(formattedMessage);
          break;
        case 'info':
          console.info(formattedMessage);
          break;
        case 'warn':
          console.warn(formattedMessage);
          break;
        case 'error':
          console.error(formattedMessage);
          break;
      }
    }
    
    this.writeToFile(formattedMessage);
  }

  debug(message: string, data?: any): void {
    this.log('debug', message, data);
  }

  info(message: string, data?: any): void {
    this.log('info', message, data);
  }

  warn(message: string, data?: any): void {
    this.log('warn', message, data);
  }

  error(message: string, data?: any): void {
    this.log('error', message, data);
  }

  // Create a child logger for a specific component
  child(component: string): Logger {
    return new Logger({
      sessionId: this.sessionId,
      component,
      toConsole: this.toConsole,
      toFile: this.toFile
    });
  }

  // Create a new logger instance for a specific session
  static forSession(sessionId: string, component?: string): Logger {
    return new Logger({
      sessionId,
      component: component || 'session'
    });
  }

  // Create a new logger instance for API routes
  static forApi(apiRoute: string, sessionId?: string): Logger {
    return new Logger({
      sessionId: sessionId || 'api',
      component: `api:${apiRoute}`
    });
  }
}

// Default application logger
const appLogger = new Logger();

export { Logger, appLogger };
