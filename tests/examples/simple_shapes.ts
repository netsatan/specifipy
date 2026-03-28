interface Drawable {
    draw(): void;
}

class Shape implements Drawable {
    name: string;
    color: string;

    constructor(name: string, color: string) {
        this.name = name;
        this.color = color;
    }

    draw(): void {
        console.log(`Drawing ${this.name}`);
    }

    getColor(): string {
        return this.color;
    }
}

class Circle extends Shape {
    radius: number;
    private center: string;

    constructor(radius: number, color: string) {
        super("circle", color);
        this.radius = radius;
        this.center = "origin";
    }

    area(): number {
        return Math.PI * this.radius * this.radius;
    }
}
