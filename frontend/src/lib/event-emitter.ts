type Listener = (...args: any[]) => void

export class EventEmitter {
  private listeners = new Map<string, Set<Listener>>()

  on(event: string, listener: Listener) {
    const listeners = this.listeners.get(event) ?? new Set<Listener>()
    listeners.add(listener)
    this.listeners.set(event, listeners)
    return this
  }

  off(event: string, listener: Listener) {
    this.listeners.get(event)?.delete(listener)
    return this
  }

  once(event: string, listener: Listener) {
    const wrapped = (...args: any[]) => {
      this.off(event, wrapped)
      listener(...args)
    }
    return this.on(event, wrapped)
  }

  emit(event: string, ...args: any[]) {
    this.listeners.get(event)?.forEach((listener) => listener(...args))
    return this
  }

  removeAllListeners(event?: string) {
    if (event) {
      this.listeners.delete(event)
    } else {
      this.listeners.clear()
    }
    return this
  }
}
