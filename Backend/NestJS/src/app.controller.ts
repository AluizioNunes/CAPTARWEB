import { Controller, Get } from '@nestjs/common'

@Controller()
export class AppController {
  @Get()
  root() {
    return { status: 'ok', service: 'nestjs' }
  }

  @Get('health')
  health() {
    return { status: 'ok' }
  }
}